"""TemplateNarrator — data-driven narrator with configurable templates.

Follows narrator-template-v1 spec and TDD §4.16.
Dispatches exactly nine events: entity_entered, action_output, error_output,
episode_completed, game_over, system_message, entity_described, item_examined,
inventory_listed. Uses payload keys, world-state descriptions, then
deterministic fallbacks. Unrelated events return None.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fortress_engine.plugins.narrator_interface import NarratorInterface

if TYPE_CHECKING:
    from fortress_engine.events.event_bus import EventBus
    from fortress_engine.events.event_types import EngineEvent
    from fortress_engine.engine.state import WorldState


# ---------------------------------------------------------------------------
# Default Spanish messages — code-driven dispatch (design.md table)
# ---------------------------------------------------------------------------

DEFAULT_SPANISH_MESSAGES: dict[str, str] = {
    # --- error_output codes ---
    "error_output.no_action": "No entiendes cómo hacer '{verb}' aquí.",
    "error_output.blocked": "No puedes ir por ahí.",
    "error_output.no_repository": "Guardar no está disponible.",
    "error_output.invalid_slot": "Ranura inválida. Usá 1, 2, o 3.",
    "error_output.missing_slot": "No hay partida guardada en la ranura {slot}.",
    "error_output.invalid_protagonist": "No se encuentra a '{name}'.",
    "error_output.operator_failed": "No puedes hacer eso.",
    "error_output.text_closed": "{passage_name} está cerrada.",
    "error_output.requires_item": "No puedes pasar por {passage_name} aún.",
    "error_output.forbids_item": "{passage_name} está sellada.",
    "error_output.requires_flag": "No puedes pasar por {passage_name} aún.",
    "error_output.forbids_flag": "{passage_name} está sellada.",
    "error_output.not_portable": "Usted no puede cargar con eso.",
    "error_output.too_heavy": "Sería demasiado peso.",
    "error_output.entity_not_found": "No se encuentra.",
    "error_output.entity_not_in_container": "No está donde lo buscas.",
    "error_output.container_not_found": "No se encuentra el destino.",
    "error_output.transform_component_missing": "No puedes hacer eso.",
    "error_output.combine_inputs_missing": "Faltan objetos para combinar.",
    "error_output.teleport_entity_not_found": "No se encuentra.",
    "error_output.teleport_anchor_not_found": "No puedes ir ahí.",
    "error_output.unknown_operator": "No puedes hacer eso.",
    "error_output.unhandled_operator": "No puedes hacer eso.",
    # --- system_message codes ---
    "system_message.game_saved": "Partida guardada en la ranura {slot}.",
    "system_message.game_loaded": "Partida cargada de la ranura {slot}.",
    "system_message.protagonist_switched": "Ahora controlas a {name}.",
    "system_message.protagonists_listed": "Grupo: {names}.",
}

# ---------------------------------------------------------------------------
# Default templates (7 keys — error_output + system_message now use the
# messages dispatch above)
# ---------------------------------------------------------------------------

_DEFAULT_TEMPLATES: dict[str, str] = {
    "entity_entered": "Entras en {entity_name}.",
    "action_output": "{text}",
    "episode_completed": "{victory_text}",
    "game_over": "Fin del juego.",
    "entity_described": "{description}",
    "entity_examined": "{description}",
    "inventory_listed": "Tienes: {items}.",
}

# ---------------------------------------------------------------------------
# Fallback text when payload keys are missing
# ---------------------------------------------------------------------------

_FALLBACK_TEXT: dict[str, str] = {
    "entity_entered": "Entras en una nueva ubicación.",
    "action_output": "Hecho.",
    "error_output": "Ha ocurrido un error.",
    "episode_completed": "Episodio completado.",
    "game_over": "Fin del juego.",
    "system_message": "Mensaje del sistema.",
    "entity_described": "No ves nada especial.",
    "entity_examined": "No ves nada especial.",
    "inventory_listed": "No tienes nada.",
}

# ---------------------------------------------------------------------------
# The nine event types this narrator handles
# ---------------------------------------------------------------------------

_TEMPLATE_EVENTS: tuple[str, ...] = (
    "entity_entered",
    "action_output",
    "error_output",
    "episode_completed",
    "game_over",
    "system_message",
    "entity_described",
    "entity_examined",
    "inventory_listed",
)


class TemplateNarrator(NarratorInterface):
    """Data-driven narrator that uses templates for nine event types.

    Accepts optional *templates* dict that overrides any default template.
    Each template may contain ``{key}`` placeholders that are filled from
    the event payload or fallback text.

    ``initialize(event_bus)`` subscribes to the nine supported event types
    and is idempotent.
    """

    def __init__(
        self,
        language: str = "es",
        templates: dict[str, str] | None = None,
        messages: dict[str, str] | None = None,
    ) -> None:
        super().__init__(language)
        self._templates = dict(_DEFAULT_TEMPLATES)
        if templates:
            self._templates.update(templates)
        self._messages = dict(DEFAULT_SPANISH_MESSAGES)
        if messages:
            self._messages.update(messages)
        self._initialized = False

    # ------------------------------------------------------------------
    # ABC properties
    # ------------------------------------------------------------------

    @property
    def language(self) -> str:
        """Return the language code for this narrator instance."""
        return self._language

    # ------------------------------------------------------------------
    # Event subscription
    # ------------------------------------------------------------------

    def initialize(self, event_bus: EventBus) -> None:
        """Subscribe to the nine template event types (idempotent)."""
        if self._initialized:
            return
        self._initialized = True

        for ev_type in _TEMPLATE_EVENTS:
            event_bus.subscribe(ev_type, self._bus_handler)

    def _bus_handler(self, event: EngineEvent) -> None:
        """Bus-side handler — discards return value; subscribers are
        fire-and-forget."""
        _ = self.handle_event(event, None)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def handle_event(
        self, event: EngineEvent, world_state: WorldState | None
    ) -> str | None:
        """Dispatch *event* to the appropriate handler.

        Returns:
            Formatted text for one of the nine supported types,
            or ``None`` for unrelated/unknown event types.
        """
        handler_name = _DISPATCH.get(event.type)
        if handler_name is None:
            return None
        handler = getattr(self, handler_name)
        return handler(event, world_state)

    # ------------------------------------------------------------------
    # Handlers — one per event type
    # ------------------------------------------------------------------

    def _handle_entity_entered(
        self, event: EngineEvent, world_state: WorldState | None
    ) -> str:
        payload = event.payload
        entity_name = payload.get("entity_name")
        if entity_name:
            text = self._templates["entity_entered"].format(entity_name=str(entity_name))
        else:
            text = _FALLBACK_TEXT["entity_entered"]
        return text

    def _handle_action_output(
        self, event: EngineEvent, world_state: WorldState | None
    ) -> str:
        text = event.payload.get("text")
        if text:
            return self._templates["action_output"].format(text=str(text))
        return _FALLBACK_TEXT["action_output"]

    def _handle_error_output(
        self, event: EngineEvent, world_state: WorldState | None
    ) -> str:
        code = event.payload.get("error_code", "")
        data = event.payload.get("data", {}) or {}
        key = f"error_output.{code}"
        template = self._messages.get(key) or _FALLBACK_TEXT["error_output"]
        try:
            return template.format(**data)
        except (KeyError, IndexError, ValueError):
            return template  # deterministic fallback, no crash

    def _handle_episode_completed(
        self, event: EngineEvent, world_state: WorldState | None
    ) -> str:
        victory_text = event.payload.get("victory_text")
        if victory_text:
            return self._templates["episode_completed"].format(victory_text=str(victory_text))
        return _FALLBACK_TEXT["episode_completed"]

    def _handle_game_over(
        self, event: EngineEvent, world_state: WorldState | None
    ) -> str:
        template = self._templates["game_over"]
        reason = event.payload.get("reason")
        if reason and "{" in template:
            return template.format(reason=str(reason))
        return template

    def _handle_system_message(
        self, event: EngineEvent, world_state: WorldState | None
    ) -> str:
        code = event.payload.get("code", "")
        data = event.payload.get("data", {}) or {}
        key = f"system_message.{code}"
        template = self._messages.get(key) or _FALLBACK_TEXT["system_message"]
        try:
            return template.format(**data)
        except (KeyError, IndexError, ValueError):
            return template  # deterministic fallback, no crash

    def _handle_entity_described(
        self, event: EngineEvent, world_state: WorldState | None
    ) -> str:
        description = event.payload.get("description")
        if description:
            return self._templates["entity_described"].format(description=str(description))
        return _FALLBACK_TEXT["entity_described"]

    def _handle_entity_examined(
        self, event: EngineEvent, world_state: WorldState | None
    ) -> str:
        description = event.payload.get("description")
        if description:
            return self._templates["entity_examined"].format(description=str(description))
        return _FALLBACK_TEXT["entity_examined"]

    def _handle_inventory_listed(
        self, event: EngineEvent, world_state: WorldState | None
    ) -> str:
        items = event.payload.get("items")
        if items:
            return self._templates["inventory_listed"].format(items=str(items))
        return _FALLBACK_TEXT["inventory_listed"]


# ---------------------------------------------------------------------------
# Dispatch table (built after class definition to reference bound methods)
# ---------------------------------------------------------------------------

_DISPATCH: dict[str, str] = {
    "entity_entered": "_handle_entity_entered",
    "action_output": "_handle_action_output",
    "error_output": "_handle_error_output",
    "episode_completed": "_handle_episode_completed",
    "game_over": "_handle_game_over",
    "system_message": "_handle_system_message",
    "entity_described": "_handle_entity_described",
    "entity_examined": "_handle_entity_examined",
    "inventory_listed": "_handle_inventory_listed",
}
