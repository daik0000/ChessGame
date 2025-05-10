import pygame
import chess
import chess.engine
from datetime import datetime
import os

# Khoi tao Pygame
pygame.init()
pygame.font.init() # Khoi tao module font

# Cai dat kich thuoc cua so
screen_width = 900
screen_height = 800
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Chess with Stockfish")

# Mau sac
white = (255, 255, 255)
black = (0, 0, 0)
light_square = (240, 217, 181)
dark_square = (181, 136, 99)
highlight_color = (255, 255, 0)
possible_move_color = (0, 255, 0, 100)
background = (200, 200, 200)
dialog_background = (220, 220, 220)
dialog_text_color = black
button_color = (100, 149, 237)
button_text_color = white

# Kich thuoc o co va vi tri ban co
square_size = 80
board_width = square_size * 8
board_height = square_size * 8
board_x = (screen_width - board_width) // 2
board_y = (screen_height - board_height) // 2

# Vi tri va kich thuoc o bo cuoc
give_up_square_size = square_size
give_up_square_x = board_x - give_up_square_size - 20
give_up_square_y = board_y + board_height - give_up_square_size
give_up_rect = pygame.Rect(give_up_square_x, give_up_square_y, give_up_square_size, give_up_square_size)

# Font chu
font_large = pygame.font.SysFont('Arial', 30)
font_medium = pygame.font.SysFont('Arial', 20)

# Tai va resize hinh anh quan co
pieces = {}
piece_names = ["wP", "wR", "wN", "wB", "wQ", "wK", "bP", "bR", "bN", "bB", "bQ", "bK"]
for name in piece_names:
    try:
        image = pygame.image.load(f"images/{name}.png").convert_alpha()
        pieces[name] = pygame.transform.scale(image, (square_size, square_size))
    except pygame.error as e:
        print(f"Error loading image {name}.png: {e}")
        pygame.quit()
        exit()

# Khoi tao ban co va engine Stockfish
STOCKFISH_PATH = "stockfish/stockfish.exe"  # Dam bao duong dan chinh xac
engine = None
try:
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
except FileNotFoundError:
    print(f"Stockfish not found at path: {STOCKFISH_PATH}")
    pygame.quit()
    exit()

board = chess.Board()
selected_square = None
possible_moves = []
giveup = False
player_moved = False # Bien theo doi xem nguoi choi da di trong luot nay chua
show_start_dialog = True
game_started = False
show_game_over_dialog = False
game_over_message = ""
game_over_buttons = []
show_give_up_dialog = False
give_up_buttons = []

# Tao thu muc 'history' neu chua ton tai
history_folder = "history"
if not os.path.exists(history_folder):
    os.makedirs(history_folder)

# Mo file de ghi lich su nuoc di voi encoding UTF-8 trong thu muc 'history'
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
history_file_path = os.path.join(history_folder, f"game_history_{timestamp}.txt")
history_file = None
try:
    history_file = open(history_file_path, "w", encoding="utf-8")
    history_file.write("Move history:\n")
except Exception as e:
    print(f"Error opening history file: {e}")
    pygame.quit()
    exit()

# Ham chuyen doi toa do Pygame sang ky hieu o co vua (dieu chinh cho vi tri ban co)
def get_square_from_pos(pos):
    col = (pos[0] - board_x) // square_size
    row = 7 - ((pos[1] - board_y) // square_size)
    if 0 <= col < 8 and 0 <= row < 8:
        return chess.square(col, row)
    return None

# Ham chuyen doi ky hieu o co vua sang toa do Pygame (dieu chinh cho vi tri ban co)
def get_pos_from_square(square):
    col = chess.square_file(square)
    row = 7 - chess.square_rank(square)
    return (board_x + col * square_size, board_y + row * square_size)

# Ham ve ban co va quan co
def draw_board_and_pieces():
    screen.fill(background)
    for row in range(8):
        for col in range(8):
            square = chess.square(col, 7 - row)
            x = board_x + col * square_size
            y = board_y + row * square_size
            color = light_square if (row + col) % 2 == 0 else dark_square
            pygame.draw.rect(screen, color, (x, y, square_size, square_size))

            # Highlight o duoc chon
            if selected_square == square:
                pygame.draw.rect(screen, highlight_color, (x, y, square_size, square_size), 5)

            # Highlight cac nuoc di kha thi
            if selected_square is not None and board.turn == chess.WHITE:
                for move in possible_moves:
                    if move.to_square == square:
                        s = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
                        s.fill(possible_move_color)
                        screen.blit(s, (x, y, square_size, square_size))

            # Ve quan co
            piece = board.piece_at(square)
            if piece:
                piece_name = f"{'w' if piece.color == chess.WHITE else 'b'}{piece.symbol().upper()}"
                screen.blit(pieces[piece_name], (x, y))

    # Ve o bo cuoc
    pygame.draw.rect(screen, white, give_up_rect)
    try:
        give_up_image = pygame.image.load("images/giveup.png").convert_alpha()
        give_up_image = pygame.transform.scale(give_up_image, (give_up_square_size, give_up_square_size))
        screen.blit(give_up_image, (give_up_square_x, give_up_square_y))
    except pygame.error as e:
        print(f"Error loading giveup.png image: {e}")

    pygame.display.flip()

def show_dialog(message, buttons):
    dialog_width = 300
    dialog_height = 150
    dialog_x = (screen_width - dialog_width) // 2
    dialog_y = (screen_height - dialog_height) // 2
    dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)

    pygame.draw.rect(screen, dialog_background, dialog_rect)
    pygame.draw.rect(screen, black, dialog_rect, 2)

    font_message = font_medium  # Su dung font_medium cho thong bao
    text_surface = font_message.render(message, True, dialog_text_color)
    text_rect = text_surface.get_rect(center=(dialog_x + dialog_width // 2, dialog_y + 40))
    screen.blit(text_surface, text_rect)

    button_rects = []
    button_width = 80
    button_height = 30
    button_spacing = 20
    start_x = dialog_x + (dialog_width - (button_width * len(buttons) + button_spacing * (len(buttons) - 1))) // 2
    y_button = dialog_y + 90

    for i, button_text in enumerate(buttons):
        button_x = start_x + i * (button_width + button_spacing)
        button_rect = pygame.Rect(button_x, y_button, button_width, button_height)
        pygame.draw.rect(screen, button_color, button_rect)
        text_surface = font_medium.render(button_text, True, button_text_color)
        text_rect = text_surface.get_rect(center=button_rect.center)
        screen.blit(text_surface, text_rect)
        button_rects.append((button_rect, button_text))

    pygame.display.flip()
    return button_rects

# Vong lap chinh cua tro choi Pygame
running = True
start_buttons = []
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            if show_start_dialog:
                for rect, text in start_buttons:
                    if rect.collidepoint(pos):
                        if text == "Go":
                            show_start_dialog = False
                            game_started = True
                        break
            elif show_game_over_dialog:
                for rect, text in game_over_buttons:
                    if rect.collidepoint(pos):
                        if text == "Exit":
                            show_game_over_dialog = False
                            running = False
                            break # Them break de thoat khoi vong lap su kien ngay lap tuc
                if not running: # Kiem tra lai running sau khi xu ly su kien Exit
                    break
            elif show_give_up_dialog:
                for rect, text in give_up_buttons:
                    if rect.collidepoint(pos):
                        if text == "Yes":
                            giveup = True
                            show_give_up_dialog = False
                            show_game_over_dialog = True
                            game_over_message = "You gave up!"
                            game_over_buttons = show_dialog(game_over_message, ["Exit"])
                        elif text == "No":
                            show_give_up_dialog = False
                        break
            elif game_started and not show_game_over_dialog and not show_give_up_dialog: # Chi xu ly di chuyen khi khong co hop thoai nao dang hien thi
                if give_up_rect.collidepoint(pos):
                    show_give_up_dialog = True
                    give_up_buttons = show_dialog("Are you sure you want to give up?", ["Yes", "No"])
                elif board.turn == chess.WHITE:
                    # Kiem tra van co ket thuc truoc khi xu ly nuoc di cua nguoi choi
                    if board.is_game_over() and not show_game_over_dialog:
                        winner = "Black" if board.turn else "White" # Turn da chuyen sang ben chien thang
                        game_over_message = ""
                        if board.is_checkmate():
                            game_over_message = f"Checkmate! Winner: {winner}"
                        elif board.is_stalemate():
                            game_over_message = "Stalemate!"
                        elif board.is_insufficient_material():
                            game_over_message = "Draw by insufficient material!"
                        elif board.is_seventyfive_moves():
                            game_over_message = "Draw by 75-move rule!"
                        elif board.is_fivefold_repetition():
                            game_over_message = "Draw by fivefold repetition!"

                        if game_over_message:
                            show_game_over_dialog = True
                            game_over_buttons = show_dialog(game_over_message, ["Exit"])
                    else:
                        clicked_square = get_square_from_pos(pos)
                        if clicked_square is not None:
                            if selected_square is None:
                                if board.piece_at(clicked_square) is not None and board.piece_at(clicked_square).color == chess.WHITE:
                                    selected_square = clicked_square
                                    possible_moves = [move for move in board.legal_moves if move.from_square == selected_square]
                            else:
                                move = chess.Move(selected_square, clicked_square)
                                if move in possible_moves:
                                    board.push(move)
                                    if history_file:
                                        history_file.write(f"White: {move.uci()}\n")
                                    selected_square = None
                                    possible_moves = []
                                    player_moved = True
                                    draw_board_and_pieces() # Ve lai sau khi nguoi choi di
                                else:
                                    if board.piece_at(clicked_square) is not None and board.piece_at(clicked_square).color == chess.WHITE:
                                        selected_square = clicked_square
                                        possible_moves = [move for move in board.legal_moves if move.from_square == selected_square]
                                    else:
                                        selected_square = None
                                        possible_moves = []

    if show_start_dialog:
        screen.fill(background)
        start_buttons = show_dialog("Let's play with me!", ["Go"])
    elif show_game_over_dialog:
        screen.fill(background) # Dam bao ve lai background de che cac thanh phan khac
        show_dialog(game_over_message, ["Exit"]) # Chi ve hop thoai ket qua
    elif show_give_up_dialog:
        screen.fill(background) # Dam bao ve lai background de che cac thanh phan khac
        give_up_buttons = show_dialog("Are you sure you want to give up?", ["Yes", "No"]) # Chi ve hop thoai bo cuoc
    else:
        draw_board_and_pieces() # Ve ban co khi khong co hop thoai nao

        # Luot cua Stockfish (chi khi nguoi choi da di va khong phai game over hoac dang bo cuoc)
        if game_started and not board.is_game_over() and board.turn == chess.BLACK and not giveup and running and player_moved and not show_game_over_dialog and not show_give_up_dialog:
            pygame.time.delay(500)
            try:
                result = engine.analyse(board, chess.engine.Limit(time=1))
                best_move = result["pv"][0]
                print(f"Stockfish moves: {best_move.uci()}")
                board.push(best_move)
                if history_file:
                    history_file.write(f"Black: {best_move.uci()}\n")
                draw_board_and_pieces() # Ve lai sau khi Stockfish di
            except chess.engine.EngineError as e:
                print(f"Engine error: {e}")
                running = False
            except chess.engine.InfoError as e:
                print(f"Engine info error: {e}")
            player_moved = False # Reset flag after Stockfish's move

        # Kiem tra ket thuc van co sau luot di cua Stockfish (da co)
        if game_started and board.is_game_over() and not show_game_over_dialog and not show_give_up_dialog:
            winner = "Black" if board.turn else "White"
            game_over_message = ""
            if board.is_checkmate():
                game_over_message = f"Checkmate! Winner: {winner}"
            elif board.is_stalemate():
                game_over_message = "Stalemate!"
            elif board.is_insufficient_material():
                game_over_message = "Draw by insufficient material!"
            elif board.is_seventyfive_moves():
                game_over_message = "Draw by 75-move rule!"
            elif board.is_fivefold_repetition():
                game_over_message = "Draw by fivefold repetition!"

            if game_over_message:
                show_game_over_dialog = True
                game_over_buttons = show_dialog(game_over_message, ["Exit"])

    pygame.display.flip()

# Dong file lich su va quit Pygame
if not running:
    if giveup and not show_game_over_dialog and history_file:
        history_file.write(f"You gave up! Move history saved to: {history_file_path}\n")
    if history_file:
        history_file.close()
    if engine is not None:
        engine.quit()
    pygame.quit()
    exit()

if engine is not None and running: # Dam bao engine chua quit neu vong lap con chay
    engine.quit()
if running:
    pygame.quit()