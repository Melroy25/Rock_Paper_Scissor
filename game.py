import cv2
import mediapipe as mp
import numpy as np
import random
import time
import threading
import pygame

# Initialize pygame mixer
pygame.mixer.init()

# Setup MediaPipe for hand detection
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.75)
mp_draw = mp.solutions.drawing_utils

# Image paths (Note: These are local paths and will not work in a web environment)
img_paths = {
    "ROCK": r"E:\Python_Projects\Rock _Paper_Scissor\rock.jpg",
    "PAPER": r"E:\Python_Projects\Rock _Paper_Scissor\paper.jpg",
    "SCISSOR": r"E:\Python_Projects\Rock _Paper_Scissor\scissor.jpg"
}

# Sound paths (Note: These are local paths and will not work in a web environment)
# Added sounds for round wins/losses as requested.
sound_paths = {
    "GAME_WIN": r"E:\Python_Projects\Rock _Paper_Scissor\winner.mp3",
    "GAME_LOSE": r"E:\Python_Projects\Rock _Paper_Scissor\loser.mp3",
    "ROUND_WIN": r"E:\Python_Projects\Rock _Paper_Scissor\win.wav",
    "ROUND_LOSE": r"E:\Python_Projects\Rock _Paper_Scissor\loose.wav",
    "DRAW": r"E:\Python_Projects\Rock _Paper_Scissor\draw.mp3"
}

# Threaded sound player using pygame
def play_sound(path):
    """Plays a sound file in a separate thread to avoid blocking the main loop."""
    def _play():
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
        except Exception as e:
            print("Sound Error:", e)
    threading.Thread(target=_play, daemon=True).start()

# Game variables
player_score = 0
ai_score = 0
game_result = ""
ai_move = "WAIT"
final_winner = None
last_round_time = time.time()
# State machine for the game round
# "COUNTDOWN": 2-second countdown before the AI's move is revealed
# "REVEAL": AI's move and result are displayed for 1 second
# "GAME_OVER": The game has a winner and is waiting to be reset
round_state = "COUNTDOWN"

# Webcam setup
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Finger Detection
def fingers_up(hand):
    """Detects which fingers are up based on landmark positions."""
    fingers = []
    tip_ids = [4, 8, 12, 16, 20]
    # Thumb check (horizontal movement)
    fingers.append(1 if hand.landmark[tip_ids[0]].x < hand.landmark[tip_ids[0] - 1].x else 0)
    # Other fingers check (vertical movement)
    for i in range(1, 5):
        fingers.append(1 if hand.landmark[tip_ids[i]].y < hand.landmark[tip_ids[i] - 2].y else 0)
    return fingers

# Detect gesture
def get_player_move(fingers):
    """Translates the number of fingers up into a game move."""
    total = fingers.count(1)
    if total == 0:
        return "ROCK"
    elif fingers[1] == 1 and fingers[2] == 1 and total == 2:
        return "SCISSOR"
    elif total == 5:
        return "PAPER"
    return "UNKNOWN"

# Game winner logic
def get_winner(player, ai):
    """Determines the winner of the round."""
    if player == ai:
        return "DRAW"
    elif (player == "ROCK" and ai == "SCISSOR") or \
         (player == "PAPER" and ai == "ROCK") or \
         (player == "SCISSOR" and ai == "PAPER"):
        return "WIN"
    return "LOSE"

# Game loop
while True:
    success, img = cap.read()
    img = cv2.flip(img, 1)

    # Define dimensions for the combined screen
    frame_width = 640
    frame_height = 480
    combined_width = frame_width + 400
    combined = np.zeros((frame_height, combined_width, 3), dtype=np.uint8)
    
    # Place camera feed on the left side
    combined[0:frame_height, 0:frame_width] = img

    # Process hand landmarks
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)
    player_move = "WAIT"

    if results.multi_hand_landmarks:
        for hand_landmark in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(combined[0:frame_height, 0:frame_width], hand_landmark, mp_hands.HAND_CONNECTIONS)
            fingers = fingers_up(hand_landmark)
            player_move = get_player_move(fingers)

    # --- Game State Logic ---
    current_time = time.time()
    
    if round_state == "COUNTDOWN":
        # Check if the 2-second countdown has passed
        if current_time - last_round_time >= 2:
            round_state = "REVEAL"
            last_round_time = current_time
            ai_move = random.choice(["ROCK", "PAPER", "SCISSOR"])
            
            if player_move in ["ROCK", "PAPER", "SCISSOR"]:
                game_result = get_winner(player_move, ai_move)
                if game_result == "WIN":
                    player_score += 1
                elif game_result == "LOSE":
                    ai_score += 1
            else:
                game_result = "UNKNOWN"
    
    elif round_state == "REVEAL":
        # Play the sound for the round outcome
        if game_result == "WIN":
            play_sound(sound_paths["ROUND_WIN"])
        elif game_result == "LOSE":
            play_sound(sound_paths["ROUND_LOSE"])
        elif game_result == "DRAW":
            play_sound(sound_paths["DRAW"])
            
        # Check if the 1-second reveal time has passed
        if current_time - last_round_time >= 1:
            # Check for a final winner
            if player_score >= 10:
                final_winner = "PLAYER"
                play_sound(sound_paths["GAME_WIN"])
                round_state = "GAME_OVER"
            elif ai_score >= 10:
                final_winner = "AI"
                play_sound(sound_paths["GAME_LOSE"])
                round_state = "GAME_OVER"
            else:
                # No winner yet, reset for next round
                round_state = "COUNTDOWN"
                last_round_time = time.time()
                ai_move = "WAIT"
                game_result = ""

    elif round_state == "GAME_OVER":
        # Game over state, wait for reset
        pass

    # --- Draw the UI on the combined screen ---

    # Main Title
    if round_state == "GAME_OVER":
        cv2.putText(combined, "GAME OVER", (frame_width + 60, 40), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 2)
    else:
        cv2.putText(combined, "PLAY YOUR MOVE", (frame_width + 50, 40), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 2)
    
    # Score Info
    cv2.putText(combined, f"You: {player_score}", (frame_width + 20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(combined, f"AI: {ai_score}", (frame_width + 250, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

    # AI move image
    if round_state == "REVEAL" and ai_move in img_paths:
        ai_img = cv2.imread(img_paths[ai_move])
        if ai_img is not None:
            ai_img = cv2.resize(ai_img, (200, 200))
            # Center the AI image in the right panel
            start_x = frame_width + (400 - 200) // 2
            start_y = 180
            combined[start_y:start_y+200, start_x:start_x+200] = ai_img

    # Game Result Text
    if round_state == "REVEAL" and game_result != "":
        color = (0, 255, 0) if game_result == "WIN" else (0, 0, 255) if game_result == "LOSE" else (255, 255, 0)
        text_size, _ = cv2.getTextSize(game_result, cv2.FONT_HERSHEY_DUPLEX, 2, 6)
        text_x = frame_width + (400 - text_size[0]) // 2
        text_y = 420
        cv2.putText(combined, game_result, (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX, 2, color, 6)
    
    # Final Winner Text
    if round_state == "GAME_OVER":
        win_text = "YOU WIN!" if final_winner == "PLAYER" else "YOU LOSE!"
        color = (0, 255, 0) if final_winner == "PLAYER" else (0, 0, 255)
        text_size, _ = cv2.getTextSize(win_text, cv2.FONT_HERSHEY_DUPLEX, 2, 6)
        text_x = frame_width + (400 - text_size[0]) // 2
        text_y = 300
        cv2.putText(combined, win_text, (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX, 2, color, 6)

    # Countdown
    if round_state == "COUNTDOWN":
        countdown = int(2 - (current_time - last_round_time)) + 1
        cv2.putText(combined, str(countdown), (270, 240), cv2.FONT_HERSHEY_DUPLEX, 5, (0, 255, 255), 8)

    # Instructions
    cv2.putText(combined, "Press 'R' to reset", (10, frame_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(combined, "Press 'Q' to quit", (10, frame_height - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Display the combined window
    cv2.imshow("Rock Paper Scissors AI Game", combined)

    key = cv2.waitKey(30)

    if key == ord('r'):
        # Reset all game variables
        player_score = 0
        ai_score = 0
        game_result = ""
        ai_move = "WAIT"
        final_winner = None
        round_state = "COUNTDOWN"
        last_round_time = time.time()
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
