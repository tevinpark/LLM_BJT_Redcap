import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import pygame
import time
import json
import os
from dotenv.main import load_dotenv

load_dotenv()

# CONFIG
# Get the sheet name directly from .env
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")

# Load and process the JSON credentials from .env
creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not creds_json_str:
    raise ValueError("GOOGLE_CREDENTIALS_JSON is missing from .env")

creds = json.loads(creds_json_str)
creds["private_key"] = creds["private_key"].replace("\\n", "\n")

# Write the credentials to a local file
GOOGLE_CREDENTIALS_FILE = "google_credentials.json"
with open(GOOGLE_CREDENTIALS_FILE, "w") as f:
    json.dump(creds, f)
REDCAP_API_URL = 'https://redcap.vumc.org/api/'
REDCAP_API_TOKEN = os.getenv("REDCAP_API_TOKEN")
REDCAP_RECORD_ID = '1'

# ---------------- UI HELPERS ----------------
def display_message(message, screen, font, color=(255, 255, 255), bgcolor=(0, 0, 0), clear=True):
    if clear:
        screen.fill(bgcolor)
    text = font.render(message, True, color)
    text_rect = text.get_rect(center=(400, 300))
    screen.blit(text, text_rect)
    pygame.display.flip()

import sys

def show_message_with_close_button(screen, font, message):
    button_color = [100, 100, 100]
    button_hover = [150, 150, 150]
    text_color = (230, 230, 230)
    button_rect = pygame.Rect(250, 350, 300, 60)
    corner_radius = 12  # Rounded corner radius

    hover_progress = 0  # used for smooth transition
    clock = pygame.time.Clock()

    while True:
        screen.fill((0, 0, 0))

        # Message
        msg_text = font.render(message, True, text_color)
        msg_rect = msg_text.get_rect(center=(400, 250))
        screen.blit(msg_text, msg_rect)

        # Hover animation
        mouse_pos = pygame.mouse.get_pos()
        is_hovering = button_rect.collidepoint(mouse_pos)
        if is_hovering:
            hover_progress = min(hover_progress + 10, 100)
        else:
            hover_progress = max(hover_progress - 10, 0)

        # Smooth interpolation of button color
        interp_color = [
            int(button_color[i] + (button_hover[i] - button_color[i]) * (hover_progress / 100))
            for i in range(3)
        ]

        # Draw rounded button
        pygame.draw.rect(screen, interp_color, button_rect, border_radius=corner_radius)

        # Button text
        button_text = font.render("Close Program", True, (255, 255, 255))
        text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, text_rect)

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.MOUSEBUTTONDOWN and is_hovering:
                pygame.quit()
                sys.exit(0)

def show_multiline_message_with_close_button(screen, font, message):
    button_color = [100, 100, 100]
    button_hover = [150, 150, 150]
    text_color = (180, 180, 180)
    highlight_color = (0, 255, 0)
    corner_radius = 12
    button_rect = pygame.Rect(250, 500, 300, 60)
    hover_progress = 0
    clock = pygame.time.Clock()

    screen.fill((0, 0, 0))
    lines = message.split('\n')

    # First line: BIG and green
    title_font = pygame.font.Font(None, 60)
    title_text = title_font.render(lines[0], True, highlight_color)
    title_rect = title_text.get_rect(center=(400, 100))
    screen.blit(title_text, title_rect)

    # Rest of the lines: smaller and gray
    small_font = pygame.font.Font(None, 36)
    y = 160
    for line in lines[1:]:
        text = small_font.render(line, True, text_color)
        rect = text.get_rect(center=(400, y))
        screen.blit(text, rect)
        y += 40

    while True:
        mouse_pos = pygame.mouse.get_pos()
        is_hovering = button_rect.collidepoint(mouse_pos)
        if is_hovering:
            hover_progress = min(hover_progress + 10, 100)
        else:
            hover_progress = max(hover_progress - 10, 0)

        # Button color interpolation
        interp_color = [
            int(button_color[i] + (button_hover[i] - button_color[i]) * (hover_progress / 100))
            for i in range(3)
        ]

        # Redraw button each frame
        pygame.draw.rect(screen, interp_color, button_rect, border_radius=corner_radius)

        # Button text
        button_font = pygame.font.Font(None, 36)
        button_text = button_font.render("Close Program", True, (255, 255, 255))
        text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, text_rect)

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.MOUSEBUTTONDOWN and is_hovering:
                return  # instead of quitting program, just exit message screen

# ---------------- INPUT ----------------
def get_participant_id(screen, font):
    input_text = ''
    active = True
    clock = pygame.time.Clock()

    while active:
        screen.fill((0, 0, 0))

        # Render prompt and input separately for color control
        prompt_surface = font.render("Enter Participant ID: ", True, (180, 180, 180))  # gray
        input_surface = font.render(input_text, True, (0, 255, 0))                     # green

        # Position side-by-side
        screen.blit(prompt_surface, (200, 280))
        screen.blit(input_surface, (200 + prompt_surface.get_width(), 280))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return input_text.strip()
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    input_text += event.unicode

        clock.tick(30)


# ---------------- SHEETS ----------------
def get_sheet_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(GOOGLE_SHEET_NAME).sheet1
    return sheet.get_all_values()

def find_participant_row(data, participant_id):
    for row in data:
        if row[0] == str(participant_id):
            return row
    return None

# ---------------- REDCAP ----------------
def get_redcap_ready_fields():
    check_data = {
        'token': REDCAP_API_TOKEN,
        'content': 'record',
        'format': 'json',
        'type': 'flat',
        'filterLogic': '[record_id] = 1',
        "fields": ",".join([
            "ready_1", "ready_2",
            "selected_participant_1", "environment_type_1", "meg_type_1",
            "selected_participant_2", "environment_type_2", "meg_type_2"
        ]),
    }

    r = requests.post(REDCAP_API_URL, data=check_data)
    result = r.json()
    print("REDCap response:", result)  # For debugging

    if not result:
        raise ValueError("REDCap returned no records matching filterLogic.")

    record = result[0]
    ready_1 = int(record.get('ready_1', 0))
    ready_2 = int(record.get('ready_2', 0))
    return ready_1, ready_2



def format_sheet_row_for_redcap(row, suffix):
    if len(row) < 9:
        raise ValueError(f"Row for participant is too short (expected at least 9 columns): {row}")

    participant_id = row[0]
    env_raw = row[6].strip()
    modality_raw = row[8].strip()

    env_map = {"Correct": 0, "Incorrect": 1, "Random": 2}
    meg_map = {
        "Audio/Visual": 0,
        "Visual/Audio": 1,
        "Audiovisual": 2
    }

    return {
        f"record_id": REDCAP_RECORD_ID,
        f"selected_participant_{suffix}": str(participant_id),
        f"environment_type_{suffix}": str(env_map.get(env_raw, "")),
        f"meg_type_{suffix}": str(meg_map.get(modality_raw, "")),
    }

def submit_to_redcap(data):
    payload = {
        'token': REDCAP_API_TOKEN,
        'content': 'record',
        'format': 'json',
        'type': 'flat',
        'data': json.dumps([data])
    }
    r = requests.post(REDCAP_API_URL, data=payload)
    return r.status_code == 200

def show_main_menu_buttons(screen, font):
    base_buttons = [
        {"label": "Participant Selection", "y": 350, "action": "participant", "base_color": [100, 100, 100], "hover_color": [150, 150, 150]},
        {"label": "Clear Selection Fields", "y": 450, "action": "clear", "base_color": [160, 50, 50], "hover_color": [200, 70, 70]}
    ]

    button_width = 400
    button_height = 60
    corner_radius = 12

    hover_progress = [0 for _ in base_buttons]
    clock = pygame.time.Clock()

    # Small hint font
    hint_font = pygame.font.Font(None, 28)

    while True:
        screen.fill((0, 0, 0))

        # Title
        title = font.render("Choose Action", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(400, 200)))

        mouse_pos = pygame.mouse.get_pos()

        for i, button in enumerate(base_buttons):
            x = 200
            y = button["y"]
            rect = pygame.Rect(x, y, button_width, button_height)

            is_hovering = rect.collidepoint(mouse_pos)
            hover_progress[i] = min(hover_progress[i] + 10, 100) if is_hovering else max(hover_progress[i] - 10, 0)

            # Color interpolation
            interp_color = [
                int(button["base_color"][c] + (button["hover_color"][c] - button["base_color"][c]) * (hover_progress[i] / 100))
                for c in range(3)
            ]

            # Draw button
            pygame.draw.rect(screen, interp_color, rect, border_radius=corner_radius)
            label_surface = font.render(button["label"], True, (255, 255, 255))
            screen.blit(label_surface, label_surface.get_rect(center=rect.center))

            # Draw hint text under red button
            if button["action"] == "clear":
                hint_text = "Clear fields only if no one is currently running an experiment"
                hint_surface = hint_font.render(hint_text, True, (180, 180, 180))
                hint_rect = hint_surface.get_rect(center=(400, y + button_height + 25))
                screen.blit(hint_surface, hint_rect)

            # Click detection
            if pygame.mouse.get_pressed()[0] and is_hovering:
                pygame.time.wait(150)
                return button["action"]

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

def show_confirm_clear_button(screen, font):
    return show_message_with_yes_no(screen, font, "Are you sure you want to clear fields?")

def show_message_with_yes_no(screen, font, message):
    yes_button = pygame.Rect(200, 350, 150, 60)
    no_button = pygame.Rect(450, 350, 150, 60)
    clock = pygame.time.Clock()

    while True:
        screen.fill((0, 0, 0))
        text = font.render(message, True, (230, 230, 230))
        screen.blit(text, text.get_rect(center=(400, 250)))

        mouse_pos = pygame.mouse.get_pos()

        for button, label, color in [
            (yes_button, "Yes", (100, 100, 100)),
            (no_button, "No", (100, 100, 100))
        ]:
            is_hovered = button.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (150, 150, 150) if is_hovered else color, button, border_radius=12)
            label_surf = font.render(label, True, (255, 255, 255))
            screen.blit(label_surf, label_surf.get_rect(center=button.center))

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if yes_button.collidepoint(event.pos):
                    return True
                elif no_button.collidepoint(event.pos):
                    return False

def clear_redcap_selection_fields():
    data = {
        "record_id": str(REDCAP_RECORD_ID),
        "selected_participant_1" : "-1",
        "selected_participant_2" : "-1",
        "ready_1": "0",
        "ready_2": "0"
    }

    payload = {
        "token": REDCAP_API_TOKEN,
        "content": "record",
        "format": "json",
        "type": "flat",
        "data": json.dumps([data])
    }

    r = requests.post(REDCAP_API_URL, data=payload)
    print("🔄 Clear readiness fields response:", r.status_code, r.text)
    return r.status_code == 200



# ---------------- MAIN ----------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    font = pygame.font.Font(None, 48)

    display_message("Connecting to REDCap...", screen, font)
    time.sleep(1)

    try:
        test = requests.post(REDCAP_API_URL, data={'token': REDCAP_API_TOKEN, 'content': 'version'})
        if test.status_code != 200:
            show_message_with_close_button(screen, font, "Failed to connect to REDCap")
            return
    except Exception as e:
        print(e)
        show_message_with_close_button(screen, font, "REDCap connection error")
        return

    display_message("Connected to REDCap", screen, font, color=(0, 255, 0))
    time.sleep(1)

    # Show action menu
    action = show_main_menu_buttons(screen, font)

    if action == "clear":
        confirm = show_confirm_clear_button(screen, font)
        if confirm:
            success = clear_redcap_selection_fields()
            if success:
                show_message_with_close_button(screen, font, "Fields cleared successfully.")
            else:
                show_message_with_close_button(screen, font, "Failed to clear fields.")
        return  # exit either way


    # 🔍 Check ready_1 and ready_2 BEFORE asking for participant ID
    try:
        ready_1, ready_2 = get_redcap_ready_fields()
        print(f"🔎 REDCap readiness: ready_1 = {ready_1}, ready_2 = {ready_2}")
        if ready_1 != 0 and ready_2 != 0:
            show_message_with_close_button(screen, font, "No fields available in REDCap")
            return
    except Exception as e:
        print("Error checking REDCap fields:", e)
        show_message_with_close_button(screen, font, "Could not read REDCap field status")
        return

    # Ask for participant ID only if a field is available
    participant_id = get_participant_id(screen, font)
    if not participant_id:
        show_message_with_close_button(screen, font, "No input. Exiting.")
        return

    display_message("Fetching data...", screen, font)
    time.sleep(1)

    try:
        sheet_data = get_sheet_data()
        row = find_participant_row(sheet_data, participant_id)
        row = find_participant_row(sheet_data, participant_id)
        if not row:
            show_message_with_close_button(screen, font, "ID not found in sheet")
            return

        # Column K (index 10) check
        if len(row) > 10 and row[10].strip().lower() == "complete":
            show_message_with_close_button(screen, font, "This participant is already marked complete.")
            return

        if ready_1 == 0:
            data = format_sheet_row_for_redcap(row, "1")
        elif ready_2 == 0:
            data = format_sheet_row_for_redcap(row, "2")

        success = submit_to_redcap(data)

        if success:
            if success:
                # Prepare a summary of the data sent
                # Determine which REDCap slot was used ("1" or "2")
                slot = "1" if ready_1 == 0 else "2"

                # Pull values from the correct keys
                env_key = str(data.get(f"environment_type_{slot}", "")).strip()
                meg_key = str(data.get(f"meg_type_{slot}", "")).strip()

                env_map = {
                    "0": "Correct (1,2,3), Incorrect (4,5,6)",
                    "1": "Incorrect (1,2,3), Correct (4,5,6)",
                    "2": "Random"
                }

                meg_map = {
                    "0": "Audio, Visual",
                    "1": "Visual, Audio",
                    "2": "Audiovisual"
                }

                participant = data.get("selectedparticipantid", "Unknown")
                env_type = env_map.get(env_key, "Unknown")
                meg_type = meg_map.get(meg_key, "Unknown")

                data_summary = (
                    f"Success!\n\n"
                    f"Selected Participant: {participant_id}\n"
                    f"Slot used: {slot} of 2\n"
                    f"Environment Type: {env_type}\n"
                    f"MEG Type: {meg_type}"
                )

                # Display the data on the screen
                show_multiline_message_with_close_button(screen, font, data_summary)

        else:
            show_message_with_close_button(screen, font, "Failed to send to REDCap")

    except Exception as e:
        print("Error:", e)
        show_message_with_close_button(screen, font, "Unexpected error occurred")

    time.sleep(4)
    pygame.quit()


if __name__ == '__main__':
    main()
