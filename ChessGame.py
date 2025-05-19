"""Một trò chơi cờ vua đơn gian với giao diện Pygame và tích hợp engine Stockfish.

File này chứa logic chính để khởi tạo trò chơi, xử lý tương tác người dùng, vẽ bàn cờ và quân cờ, giao tiếp với engine Stockfish để đối thủ AI đi, và quản lý các trạng thái của trò chơi như chọn quân, di chuyển, kết thúc ván.
"""
import pygame
import chess
import chess.engine
from datetime import datetime
import os
import sys

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
check_color = (255, 0, 0) # Mau do cho o vua bi chieu

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

# Bien luu trang thai khoi tao tai nguyen
_resources_initialized = False
pieces = {}
background_image = None
font_large = None
font_medium = None

# Khoi tao ban co va engine Stockfish (chi dinh nghia, khoi tao sau)
STOCKFISH_PATH = "stockfish\\stockfish.exe"  # Dam bao duong dan chinh xac
engine = None
board = chess.Board()
selected_square = None
possible_moves = []
giveup = False
player_moved = False # Bien theo doi xem nguoi choi da di trong luot nay chua
show_start_dialog = True
show_color_choice_dialog = False
show_difficulty_choice_dialog = False # Them bien cho hop thoai chon do kho
stockfish_level = None # Luu tru muc do kho da chon
user_color = None # Mau cua nguoi choi
bot_color = None # Mau cua bot
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

# Mo file de ghi lich su nuoc di voi encoding UTF-8 trong thu muc 'history' (khoi tao sau)
history_file_path = os.path.join(history_folder, f"game_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
history_file = None

def init_resources():
    """Khởi tạo Pygame và tải các tài nguyên cần thiết (hình ảnh, font)."""
    global _resources_initialized, pieces, background_image, font_large, font_medium

    if _resources_initialized:
        return

    pygame.init()
    pygame.font.init()

    # Font chu
    font_large = pygame.font.SysFont('Arial', 30)
    font_medium = pygame.font.SysFont('Arial', 20)

    # Tai va resize hinh anh quan co
    piece_names = ["wP", "wR", "wN", "wB", "wQ", "wK", "bP", "bR", "bN", "bB", "bQ", "bK"]
    for name in piece_names:
        try:
            image = pygame.image.load(f"images/{name}.png").convert_alpha()
            pieces[name] = pygame.transform.scale(image, (square_size, square_size))
        except pygame.error as e:
            print(f"Loi khi tai hinh anh {name}.png: {e}")
            pygame.quit()
            sys.exit()

    # Tai va resize hinh anh background
    try:
        background_image = pygame.image.load("images/start_background.png").convert() # Thay "start_background.png" bang ten file anh cua ban
        background_image = pygame.transform.scale(background_image, (screen_width, screen_height))
    except pygame.error as e:
        print(f"Loi khi tai hinh anh background: {e}")
        pygame.quit()
        sys.exit()

    _resources_initialized = True

def init_engine_and_history():
    """Khởi tạo engine Stockfish và mở file lịch sử."""
    global engine, history_file

    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except FileNotFoundError:
        print(f"Khong tim thay Stockfish tai duong dan: {STOCKFISH_PATH}")
        pygame.quit()
        sys.exit()

    try:
        history_file = open(history_file_path, "w", encoding="utf-8")
    except Exception as e:
        print(f"Loi khi mo file lich su: {e}")
        pygame.quit()
        sys.exit()

# Ham chuyen doi toa do Pygame sang ky hieu o co vua (dieu chinh cho vi tri ban co)
def get_square_from_pos(pos):
    """Chuyển đổi tọa độ Pygame (x, y) thành ký hiệu ô cờ vua.

    Hàm này nhận một tuple (x, y) là tọa độ chuột trên màn hình Pygame
    và trả về ký hiệu ô cờ vua tương ứng (ví dụ: 'a1', 'h8'). Nó cũng
    xử lý trường hợp bàn cờ bị xoay nếu người chơi chọn màu đen.

    Args:
        pos (tuple): Tuple (x, y) chứa tọa độ chuột trên màn hình.

    Returns:
        str or None: Ký hiệu ô cờ vua (ví dụ: 'a1') nếu tọa độ nằm trong bàn cờ,
                    ngược lại trả về None.
    """
    col_pygame = (pos[0] - board_x) // square_size
    row_pygame = (pos[1] - board_y) // square_size
    if 0 <= col_pygame < 8 and 0 <= row_pygame < 8:
        # Dao nguoc hang va cot neu nguoi choi chon den
        board_col = col_pygame if user_color == chess.WHITE else 7 - col_pygame
        board_row = 7 - row_pygame if user_color == chess.WHITE else row_pygame
        return chess.square(board_col, board_row)
    return None

# Ham chuyen doi ky hieu o co vua sang toa do Pygame (dieu chinh cho vi tri ban co)
def get_pos_from_square(square):
    """Chuyển đổi ký hiệu ô cờ vua thành tọa độ Pygame (x, y).

    Hàm này nhận một ký hiệu ô cờ vua (ví dụ: 'a1') và trả về
    tuple (x, y) là tọa độ góc trên bên trái của ô đó trên màn hình Pygame.
    Nó cũng xử lý trường hợp bàn cờ bị xoay nếu người chơi chọn màu đen.

    Args:
        square (chess.Square): Ký hiệu ô cờ vua.

    Returns:
        tuple: Tuple (x, y) chứa tọa độ Pygame của ô cờ.
    """
    col = chess.square_file(square)
    row = chess.square_rank(square)
    # Dao nguoc hang va cot neu nguoi choi chon den
    draw_col = col if user_color == chess.WHITE else 7 - col
    draw_row = 7 - row if user_color == chess.WHITE else row
    return (board_x + draw_col * square_size, board_y + draw_row * square_size)

# Ham ve ban co va quan co
def draw_board_and_pieces():
    """Vẽ bàn cờ, các quân cờ và các hiệu ứng đặc biệt lên màn hình.

    Hàm này vẽ các ô vuông của bàn cờ với màu sắc xen kẽ,
    highlight ô được chọn, hiển thị các nước đi khả thi và vẽ các quân cờ
    ở vị trí hiện tại trên bàn cờ. Nó cũng đánh dấu ô vua đang bị chiếu.
    """
    init_resources()
    screen.fill(background)
    checked_king_square = None
    if board.is_check():
        current_color = board.turn
        for s in chess.SQUARES:
            p = board.piece_at(s)
            if p is not None and p.piece_type == chess.KING and p.color == current_color:
                checked_king_square = s
                break

    for row in range(8):
        for col in range(8):
            # Dieu chinh thu tu row va col neu nguoi choi chon den
            draw_row = row if user_color == chess.WHITE else 7 - row
            draw_col = col if user_color == chess.WHITE else 7 - col
            square = chess.square(draw_col, 7 - draw_row)
            x = board_x + col * square_size
            y = board_y + row * square_size
            color = light_square if (row + col) % 2 == 0 else dark_square
            pygame.draw.rect(screen, color, (x, y, square_size, square_size))

            # Highlight o duoc chon
            if selected_square == square:
                pygame.draw.rect(screen, highlight_color, (x, y, square_size, square_size), 5)

            # Highlight cac nuoc di kha thi
            if selected_square is not None and board.turn == user_color:
                for move in possible_moves:
                    # Kiem tra va highlight dua tren ban co goc, khong phai ban co xoay
                    if move.to_square == chess.square(col if user_color == chess.WHITE else 7 - col, 7 - (row if user_color == chess.WHITE else 7 - row)):
                        s = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
                        s.fill(possible_move_color)
                        screen.blit(s, (x, y, square_size, square_size))

            # Ve quan co
            piece = board.piece_at(square)
            if piece:
                piece_name = f"{'w' if piece.color == chess.WHITE else 'b'}{piece.symbol().upper()}"
                screen.blit(pieces[piece_name], (x, y))

            # Hien thi o do neu vua bi chieu
            if square == checked_king_square:
                pygame.draw.rect(screen, check_color, (x, y, square_size, square_size), 5) # Ve vien do

    # Ve o bo cuoc (vi tri khong doi)
    pygame.draw.rect(screen, white, give_up_rect)
    try:
        give_up_image = pygame.image.load("images/giveup.png").convert_alpha()
        give_up_image = pygame.transform.scale(give_up_image, (give_up_square_size, give_up_square_size))
        screen.blit(give_up_image, (give_up_square_x, give_up_square_y))
    except pygame.error as e:
        print(f"Loi khi tai hinh anh giveup.png: {e}")

    pygame.display.flip()

def show_dialog(message, buttons):
    """Hiển thị một hộp thoại đơn giản với thông báo và các nút tùy chọn.

    Args:
        message (str): Nội dung thông báo hiển thị trong hộp thoại.
        buttons (list): Danh sách các chuỗi văn bản hiển thị trên các nút.

    Returns:
        list: Danh sách các tuple, mỗi tuple chứa một đối tượng pygame.Rect
              và văn bản tương ứng của nút.
    """
    init_resources()
    dialog_width = 300
    dialog_height = 150
    dialog_x = (screen_width - dialog_width) // 2
    dialog_y = (screen_height - dialog_height) // 2
    dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)

    pygame.draw.rect(screen, dialog_background, dialog_rect)
    pygame.draw.rect(screen, black, dialog_rect, 2)

    font_message = font_medium
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

def show_color_choice(message, buttons):
    """Hiển thị hộp thoại lựa chọn màu cho người chơi.

    Args:
        message (str): Nội dung thông báo hiển thị trong hộp thoại.
        buttons (list): Danh sách các chuỗi văn bản hiển thị trên các nút (ví dụ: ["White", "Black"]).

    Returns:
        list: Danh sách các tuple, mỗi tuple chứa một đối tượng pygame.Rect
              và văn bản tương ứng của nút.
    """
    init_resources()
    dialog_width = 300
    dialog_height = 150
    dialog_x = (screen_width - dialog_width) // 2
    dialog_y = (screen_height - dialog_height) // 2
    dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)

    pygame.draw.rect(screen, dialog_background, dialog_rect)
    pygame.draw.rect(screen, black, dialog_rect, 2)

    font_message = font_medium
    text_surface = font_message.render(message, True, dialog_text_color)
    text_rect = text_surface.get_rect(center=(dialog_x + dialog_width // 2, dialog_y + 40))
    screen.blit(text_surface, text_rect)

    button_rects = []
    button_width = 80
    button_height = 30
    button_spacing = 20
    start_x = dialog_x + (dialog_width - (button_width * len(buttons)+ button_spacing * (len(buttons) - 1))) // 2
    y_button = dialog_y + 90

    for i, button_text in enumerate(buttons):
        button_x = start_x + i * (button_width + button_spacing)
        button_rect= pygame.Rect(button_x, y_button, button_width, button_height)
        pygame.draw.rect(screen, button_color, button_rect)
        text_surface = font_medium.render(button_text, True, button_text_color)
        text_rect = text_surface.get_rect(center=button_rect.center)
        screen.blit(text_surface, text_rect)
        button_rects.append((button_rect, button_text))

    pygame.display.flip()
    return button_rects

def reset_game():
    """Khởi tạo lại trạng thái trò chơi về ban đầu.

    Hàm này đặt lại bàn cờ, các biến trạng thái liên quan đến trò chơi,
    đóng file lịch sử hiện tại và tạo một file lịch sử mới.
    """
    global board, selected_square, possible_moves, giveup, player_moved
    global show_start_dialog, show_color_choice_dialog, show_difficulty_choice_dialog
    global stockfish_level, user_color, bot_color, game_started, show_game_over_dialog
    global game_over_message, game_over_buttons, show_give_up_dialog, give_up_buttons
    global history_file, history_file_path

    board = chess.Board()
    selected_square = None
    possible_moves = []
    giveup = False
    player_moved = False
    show_start_dialog = True
    show_color_choice_dialog = False
    show_difficulty_choice_dialog = False
    stockfish_level = None
    user_color = None
    bot_color = None
    game_started = False
    show_game_over_dialog = False
    game_over_message = ""
    game_over_buttons = []
    show_give_up_dialog = False
    give_up_buttons = []

    # Dong file lich su cu neu co
    if history_file:
        history_file.close()
        history_file = None

    # Tao file lich su moi
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file_path = os.path.join(history_folder, f"game_history_{timestamp}.txt")
    try:
        history_file = open(history_file_path, "w", encoding="utf-8")
    except Exception as e:
        print(f"Loi khi mo file lich su: {e}")
        pygame.quit()
        sys.exit()

# Khoi tao engine va file lich su khi bat dau tro choi (moved to if __name__ == "__main__":)
# init_engine_and_history()

# Vong lap chinh cua tro choi Pygame
running = True
start_buttons = []
color_choice_buttons = []
difficulty_choice_buttons = []

if __name__ == "__main__":
    init_resources()
    init_engine_and_history()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if show_start_dialog:
                    start_buttons = show_dialog("Play with me!", ["Start"])
                    for rect, text in start_buttons:
                        if rect.collidepoint(pos):
                            if text == "Start":
                                show_start_dialog = False
                                show_color_choice_dialog = True
                                break
                elif show_color_choice_dialog:
                    color_choice_buttons = show_color_choice("Choose your color:", ["White", "Black"])
                    for rect, text in color_choice_buttons:
                        if rect.collidepoint(pos):
                            if text == "White":
                                user_color = chess.WHITE
                                bot_color = chess.BLACK
                                show_color_choice_dialog = False
                                show_difficulty_choice_dialog = True
                            elif text == "Black":
                                user_color = chess.BLACK
                                bot_color = chess.WHITE
                                show_color_choice_dialog = False
                                show_difficulty_choice_dialog = True
                            break
                elif show_difficulty_choice_dialog:
                    difficulty_choice_buttons = show_dialog("Choose difficulty:", ["Easy", "Medium", "Hard"])
                    for rect, text in difficulty_choice_buttons:
                        if rect.collidepoint(pos):
                            if text == "Easy":
                                stockfish_level = 2 # Skill Level 2 for easy
                            elif text == "Medium":
                                stockfish_level = 10 # Skill Level 10 for medium
                            elif text == "Hard":
                                stockfish_level = 20 # Skill Level 20 for hard
                            if stockfish_level is not None and engine is not None:
                                engine.configure({"Skill Level": stockfish_level})
                                game_started = True
                                show_difficulty_choice_dialog = False
                                if user_color == chess.BLACK:
                                    # Bot moves first if player chooses black
                                    try:
                                        result = engine.analyse(
                                            board, chess.engine.Limit(time=1))
                                        best_move = result["pv"][0]
                                        print(f"Stockfish (White) moves first: {best_move.uci()}")
                                        board.push(best_move)
                                        if history_file:
                                            history_file.write(f"White (Stockfish): {best_move.uci()}\n")
                                        draw_board_and_pieces()
                                        player_moved = False # Reset after bot's move
                                    except chess.engine.EngineError as e:
                                        print(f"Engine error: {e}")
                                        running = False
                                    except chess.engine.InfoError as e:
                                        print(f"Engine info error: {e}")
                                break
                elif show_game_over_dialog:
                    for rect, text in game_over_buttons:
                        if rect.collidepoint(pos):
                            if text == "Quit":
                                show_game_over_dialog = False
                                running = False
                                break
                            elif text == "Play Again":
                                show_game_over_dialog = False
                                reset_game()
                                break
                    if not running:
                        break
                elif show_give_up_dialog:
                    for rect, text in give_up_buttons:
                        if rect.collidepoint(pos):
                            if text == "Yes":
                                giveup = True
                                show_give_up_dialog = False
                                show_game_over_dialog = True
                                game_over_message = "You gave up!"
                                game_over_buttons = show_dialog(game_over_message, ["Quit", "Play Again"])
                            elif text == "No":
                                show_give_up_dialog = False
                            break
                elif game_started and not show_game_over_dialog and not show_give_up_dialog: # Handle moves only when no dialog is shown
                    if board.turn == user_color:
                        if give_up_rect.collidepoint(pos):
                            show_give_up_dialog = True
                            give_up_buttons = show_dialog("Are you sure you want to give up?", ["Yes", "No"])
                        else:
                            clicked_square = get_square_from_pos(pos)
                            if clicked_square is not None:
                                if selected_square is None:
                                    if board.piece_at(clicked_square) is not None and board.piece_at(clicked_square).color == user_color:
                                        selected_square = clicked_square
                                        possible_moves = [move for move in board.legal_moves if move.from_square == selected_square]
                                else:
                                    move = chess.Move(selected_square, clicked_square)
                                    if move in possible_moves:
                                        board.push(move)
                                        if history_file:
                                            history_file.write(f"{'Black' if user_color == chess.BLACK else 'White'}: {move.uci()}\n")
                                        selected_square = None
                                        possible_moves = []
                                        player_moved = True
                                        draw_board_and_pieces() # Redraw after player's move
                                    else:
                                        if board.piece_at(clicked_square) is not None and board.piece_at(clicked_square).color == user_color:
                                            selected_square = clicked_square
                                            possible_moves = [move for move in board.legal_moves if move.from_square == selected_square]
                                        else:
                                            selected_square = None
                                            possible_moves = []

        if show_start_dialog:
            screen.blit(background_image, (0, 0)) # Draw background image
            start_buttons = show_dialog("Play with me!", ["Start"])
        elif show_color_choice_dialog:
            screen.fill(background)
            color_choice_buttons = show_color_choice("Choose your color:", ["White", "Black"])
        elif show_difficulty_choice_dialog:
            screen.fill(background)
            difficulty_choice_buttons = show_dialog("Choose difficulty:", ["Easy", "Medium", "Hard"])
        elif show_game_over_dialog:
            screen.fill(background) # Ensure background is redrawn to cover other elements
            game_over_buttons = show_dialog(game_over_message, ["Quit", "Play Again"]) # Add Play Again button
        elif show_give_up_dialog:
            screen.fill(background) # Ensure background is redrawn to cover other elements
            give_up_buttons = show_dialog("Are you sure you want to give up?", ["Yes", "No"]) # Only draw give up dialog
        else:
            draw_board_and_pieces() # Draw the board when no dialog is active

        # Stockfish's turn
        if game_started and not board.is_game_over() and board.turn == bot_color and not giveup and running and player_moved and not show_game_over_dialog and not show_give_up_dialog:
            pygame.time.delay(500)
            try:
                result = engine.analyse(board, chess.engine.Limit(time=1))
                best_move = result["pv"][0]
                board.push(best_move)
                if history_file:
                    history_file.write(f"{'White' if bot_color == chess.WHITE else 'Black'} (Stockfish): {best_move.uci()}\n")
                draw_board_and_pieces() # Redraw after Stockfish's move
            except chess.engine.EngineError as e:
                print(f"Engine error: {e}")
                running = False
            except chess.engine.InfoError as e:
                print(f"Engine info error: {e}")
            player_moved = False # Reset flag after Stockfish's move

        # Check for game over
        if game_started and board.is_game_over() and not show_game_over_dialog and not show_give_up_dialog:
            pygame.time.delay(1000)
            winner = "Black" if board.turn else "White"
            game_over_message = ""
            if board.is_checkmate():
                game_over_message = f"Checkmate! Winner: {winner}"
            elif board.is_stalemate():
                game_over_message = "Stalemate!"
            elif board.is_insufficient_material():
                game_over_message = "Draw due to insufficient material!"
            elif board.is_seventyfive_moves():
                game_over_message = "Draw by 75-move rule!"
            elif board.is_fivefold_repetition():
                game_over_message = "Draw by fivefold repetition!"
            if history_file:
                history_file.write(f"{game_over_message}\n")
            if game_over_message:
                show_game_over_dialog = True
                game_over_buttons = show_dialog(game_over_message, ["Quit", "Play Again"]) # Add Play Again button

        pygame.display.flip()

    # Close history file and quit Pygame
    if not running:
        if giveup and not show_game_over_dialog and history_file:
            history_file.write(f"You gave up! Game history saved to: {history_file_path}\n")
        if history_file:
            history_file.close()
        if engine is not None:
            engine.quit()
        pygame.quit()
        sys.exit()

    if engine is not None and running: # Ensure engine is not quit if the loop is still running
        engine.quit()
    if running:
        pygame.quit()
        sys.exit()