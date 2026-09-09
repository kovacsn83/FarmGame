import pygame

from challenge import ChallengeStatus
from clipboard_utils import copy_text_to_clipboard
from constants import COLOR_TEXT
from game_version import get_game_version
from money_format import format_money
from player_profile import get_player_id, get_player_name
from screen_layout import get_screen_center, get_screen_size
from ui import (
    CROP_CARD_BACKGROUND, CROP_CARD_HOVER, INFO_PANEL_BACKGROUND,
    INFO_PANEL_BORDER, is_outside_popup_click,
)


PANEL_WIDTH = 720
PANEL_HEIGHT = 570
PADDING = 28
BUTTON_HEIGHT = 38
COPY_BUTTON_WIDTH = 105
COPY_FEEDBACK_MS = 1800


class GameDataPanel:
    """A központi profil-, farm-, verzió- és Challenge-adatok olvasási nézete."""

    def __init__(self):
        self.visible = False
        self.player_profile = None
        self.game_state = None
        self.submission_controller = None
        self.rect = pygame.Rect(0, 0, PANEL_WIDTH, PANEL_HEIGHT)
        self.player_copy_rect = pygame.Rect(0, 0, 0, 0)
        self.game_copy_rect = pygame.Rect(0, 0, 0, 0)
        self.close_rect = pygame.Rect(0, 0, 180, BUTTON_HEIGHT)
        self.submit_rect = pygame.Rect(0, 0, 240, BUTTON_HEIGHT)
        self.leaderboard_rect = pygame.Rect(0, 0, 210, BUTTON_HEIGHT)
        self.pending_leaderboard_request = False
        self.copy_feedback = {}
        self._update_layout()

    def open(self, player_profile, game_state=None, submission_controller=None):
        self.player_profile = player_profile
        self.game_state = game_state
        self.submission_controller = submission_controller
        self.copy_feedback.clear()
        self.pending_leaderboard_request = False
        self.visible = True
        self._update_layout()
        data = self.get_display_data()
        self._layout_challenge_buttons(
            data["submission_status"] in ("not_submitted", "failed"),
        )

    def close(self):
        self.visible = False

    def take_leaderboard_request(self):
        requested = self.pending_leaderboard_request
        self.pending_leaderboard_request = False
        return requested

    def _update_layout(self):
        width, height = get_screen_size()
        self.rect.size = (
            min(PANEL_WIDTH, max(360, width - 20)),
            min(PANEL_HEIGHT, max(420, height - 20)),
        )
        self.rect.center = get_screen_center()
        copy_x = self.rect.right - PADDING - COPY_BUTTON_WIDTH
        self.player_copy_rect = pygame.Rect(
            copy_x, self.rect.top + 142, COPY_BUTTON_WIDTH, BUTTON_HEIGHT,
        )
        self.game_copy_rect = pygame.Rect(
            copy_x, self.rect.top + 241, COPY_BUTTON_WIDTH, BUTTON_HEIGHT,
        )
        self.close_rect.center = (self.rect.centerx, self.rect.bottom - 38)
        self.submit_rect.center = (self.rect.centerx, self.rect.bottom - 88)
        if self.rect.width >= 540:
            gap = 16
            total = self.submit_rect.width + gap + self.leaderboard_rect.width
            self.submit_rect.left = self.rect.centerx - total // 2
            self.leaderboard_rect.topleft = (
                self.submit_rect.right + gap, self.submit_rect.top,
            )
        else:
            self.leaderboard_rect.center = (
                self.rect.centerx, self.rect.bottom - 138,
            )

    def _layout_challenge_buttons(self, show_submit):
        if not show_submit:
            self.leaderboard_rect.center = (
                self.rect.centerx, self.rect.bottom - 88,
            )

    def get_display_data(self):
        """Mindig az aktuális központi objektumokból olvas, másolatot nem tárol."""
        game_id = getattr(self.game_state, "game_id", None)
        challenge_manager = getattr(self.game_state, "challenge_manager", None)
        if self.game_state is None or challenge_manager is None:
            challenge_status = "Nincs aktív játék"
            farm_value = None
        elif challenge_manager.status is ChallengeStatus.COMPLETED:
            challenge_status = "Teljesítve"
            farm_value = challenge_manager.result.farm_value
        elif challenge_manager.status is ChallengeStatus.LEGACY_INELIGIBLE:
            challenge_status = "Nem érhető el (korábbi mentés)"
            farm_value = None
        else:
            challenge_status = "Folyamatban"
            farm_value = None
        local_result = (
            self.submission_controller.get_record(game_id)
            if self.submission_controller is not None and game_id else None
        )
        submission_status = (
            local_result.submission_status if local_result is not None else None
        )
        return {
            "player_name": get_player_name(self.player_profile),
            "player_id": get_player_id(self.player_profile),
            "game_id": game_id,
            "game_version": get_game_version(),
            "challenge_status": challenge_status,
            "farm_value": farm_value,
            "submission_status": submission_status,
        }

    def _copy(self, key, value, current_ticks=None):
        if not value or not copy_text_to_clipboard(value):
            return False
        now = pygame.time.get_ticks() if current_ticks is None else current_ticks
        self.copy_feedback[key] = int(now) + COPY_FEEDBACK_MS
        return True

    def handle_event(self, event, current_ticks=None):
        if not self.visible:
            return False
        self._update_layout()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        if event.type != pygame.MOUSEBUTTONDOWN:
            return event.type in (
                pygame.KEYDOWN, pygame.KEYUP, pygame.TEXTINPUT,
                pygame.MOUSEWHEEL,
            )
        if event.button != 1:
            return True
        if is_outside_popup_click(event, self.rect):
            self.close()
            return True
        data = self.get_display_data()
        self._layout_challenge_buttons(
            data["submission_status"] in ("not_submitted", "failed"),
        )
        if self.player_copy_rect.collidepoint(event.pos):
            self._copy("player_id", data["player_id"], current_ticks)
        elif data["game_id"] and self.game_copy_rect.collidepoint(event.pos):
            self._copy("game_id", data["game_id"], current_ticks)
        elif (
            self.submit_rect.collidepoint(event.pos)
            and data["submission_status"] in ("not_submitted", "failed")
            and self.submission_controller is not None
            and not self.submission_controller.submitting
        ):
            self.submission_controller.request_for_game(data["game_id"])
        elif self.leaderboard_rect.collidepoint(event.pos):
            self.pending_leaderboard_request = True
        elif self.close_rect.collidepoint(event.pos):
            self.close()
        return True

    @staticmethod
    def _draw_text(screen, font, text, x, y, color=COLOR_TEXT):
        screen.blit(font.render(str(text), True, color), (x, y))

    def _draw_button(self, screen, font, rect, label, enabled=True):
        color = CROP_CARD_BACKGROUND
        if enabled and rect.collidepoint(pygame.mouse.get_pos()):
            color = CROP_CARD_HOVER
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 1)
        text_color = COLOR_TEXT if enabled else (130, 130, 125)
        rendered = font.render(label, True, text_color)
        screen.blit(rendered, rendered.get_rect(center=rect.center))

    def draw(self, screen, font, current_ticks=None):
        if not self.visible:
            return
        self._update_layout()
        now = pygame.time.get_ticks() if current_ticks is None else int(current_ticks)
        data = self.get_display_data()
        self._layout_challenge_buttons(
            data["submission_status"] in ("not_submitted", "failed"),
        )
        pygame.draw.rect(screen, INFO_PANEL_BACKGROUND, self.rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, self.rect, 2)
        x = self.rect.left + PADDING
        self._draw_text(screen, font, "Játékadatok", x, self.rect.top + 20)
        self._draw_text(screen, font, "Játékos neve:", x, self.rect.top + 67)
        self._draw_text(screen, font, data["player_name"] or "—", x + 190, self.rect.top + 67)
        self._draw_text(screen, font, "Játékosazonosító:", x, self.rect.top + 112)
        self._draw_text(screen, font, data["player_id"] or "—", x, self.rect.top + 146)
        player_label = "Másolva" if self.copy_feedback.get("player_id", 0) > now else "Másolás"
        self._draw_button(screen, font, self.player_copy_rect, player_label, bool(data["player_id"]))

        self._draw_text(screen, font, "Játékazonosító:", x, self.rect.top + 211)
        self._draw_text(
            screen, font, data["game_id"] or "Nincs aktív játék",
            x, self.rect.top + 245,
        )
        game_label = "Másolva" if self.copy_feedback.get("game_id", 0) > now else "Másolás"
        self._draw_button(screen, font, self.game_copy_rect, game_label, bool(data["game_id"]))
        self._draw_text(screen, font, "Játékverzió:", x, self.rect.top + 302)
        self._draw_text(screen, font, data["game_version"], x + 190, self.rect.top + 302)

        challenge_y = min(self.rect.top + 330, self.rect.bottom - 220)
        self._draw_text(screen, font, "10 éves Challenge", x, challenge_y)
        self._draw_text(screen, font, f"Állapot: {data['challenge_status']}", x,
                        challenge_y + 32)
        result = "—" if data["farm_value"] is None else format_money(data["farm_value"])
        self._draw_text(screen, font, f"Farmérték: {result}", x,
                        challenge_y + 62)
        status_labels = {
            "not_submitted": "Nincs beküldve",
            "failed": "Nincs beküldve (újrapróbálható)",
            "submitted": "Beküldve",
        }
        submission = status_labels.get(data["submission_status"], "—")
        self._draw_text(screen, font, f"Ranglista: {submission}", x,
                        challenge_y + 92)
        if data["submission_status"] in ("not_submitted", "failed"):
            submitting = (
                self.submission_controller is not None
                and self.submission_controller.submitting
            )
            self._draw_button(
                screen, font, self.submit_rect,
                "Beküldés..." if submitting else "Beküldés a ranglistára",
                not submitting,
            )
        self._draw_button(
            screen, font, self.leaderboard_rect, "Top 10 ranglista",
        )
        self._draw_button(screen, font, self.close_rect, "Bezárás")
