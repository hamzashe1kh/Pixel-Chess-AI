import pygame
import chess
import chess.polyglot
import random
import math
import sys
import os
import threading 
import queue
import json
import time

# --- [ START OF AI CODE ] ---
pawn_table = [0,0,0,0,0,0,0,0,50,50,50,50,50,50,50,50,10,10,20,30,30,20,10,10,5,5,10,25,25,10,5,5,0,0,0,20,20,0,0,0,5,-5,-10,0,0,-10,-5,5,5,10,10,-20,-20,10,10,5,0,0,0,0,0,0,0,0]
knight_table = [-50,-40,-30,-30,-30,-30,-40,-50,-40,-20,0,0,0,0,-20,-40,-30,0,10,15,15,10,0,-30,-30,5,15,20,20,15,5,-30,-30,0,15,20,20,15,0,-30,-30,5,10,15,15,10,5,-30,-40,-20,0,5,5,0,-20,-40,-50,-40,-30,-30,-30,-30,-40,-50]
bishop_table = [-20,-10,-10,-10,-10,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,10,10,5,0,-10,-10,5,5,10,10,5,5,-10,-10,0,10,10,10,10,0,-10,-10,10,10,10,10,10,10,-10,-10,5,0,0,0,0,5,-10,-20,-10,-10,-10,-10,-10,-10,-20]
rook_table = [0,0,0,0,0,0,0,0,5,10,10,10,10,10,10,5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,0,0,0,5,5,0,0,0]
queen_table = [-20,-10,-10,-5,-5,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,5,5,5,0,-10,-5,0,5,5,5,5,0,-5,0,0,5,5,5,5,0,-5,-10,5,5,5,5,5,0,-10,-10,0,5,0,0,0,0,-10,-20,-10,-10,-5,-5,-10,-10,-20]
king_mg_table = [-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-20,-30,-30,-40,-40,-30,-30,-20,-10,-20,-20,-20,-20,-20,-20,-10,20,20,0,0,0,0,20,20,20,30,10,0,0,10,30,20]
king_eg_table = [-50,-40,-30,-20,-20,-30,-40,-50,-30,-20,-10,0,0,-10,-20,-30,-30,-10,20,30,30,20,-10,-30,-30,-10,30,40,40,30,-10,-30,-30,-10,30,40,40,30,-10,-30,-30,-10,20,30,30,20,-10,-30,-30,-30,0,0,0,0,-30,-30,-50,-30,-30,-30,-30,-30,-30,-50]
piece_square_tables = { chess.PAWN: pawn_table, chess.KNIGHT: knight_table, chess.BISHOP: bishop_table, chess.ROOK: rook_table, chess.QUEEN: queen_table, chess.KING: king_mg_table }
piece_values = { chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000 }

pawn_shield_value = 15
passed_pawn_bonus = [0, 10, 30, 60, 100, 150, 200, 0]
ROOK_OPEN_FILE_BONUS = 20
ROOK_SEMI_OPEN_FILE_BONUS = 10
MOBILITY_BONUS_PER_MOVE = 2

EXACT_FLAG, LOWERBOUND_FLAG, UPPERBOUND_FLAG = 0, 1, 2
TIME_UP_FLAG = -999999

def is_endgame(b):
    queens = sum(1 for s in chess.SQUARES if b.piece_at(s) and b.piece_at(s).piece_type == chess.QUEEN)
    minors = sum(1 for s in chess.SQUARES if b.piece_at(s) and b.piece_at(s).piece_type in [chess.KNIGHT, chess.BISHOP])
    return queens == 0 or (queens == 2 and minors <= 2)

def evaluate_board(b):
    if b.is_checkmate(): return -float('inf') if b.turn == chess.WHITE else float('inf')
    if b.is_stalemate() or b.is_insufficient_material() or b.is_seventyfive_moves() or b.is_fivefold_repetition() or b.is_repetition(3): return 0
    t_eval = 0
    ieg_flag = is_endgame(b)
    for square in chess.SQUARES:
        piece = b.piece_at(square)
        if not piece: continue
        table = king_eg_table if ieg_flag and piece.piece_type == chess.KING else piece_square_tables.get(piece.piece_type)
        pst_value = table[chess.square_mirror(square)] if piece.color == chess.BLACK else table[square] if table else 0
        piece_value = piece_values[piece.piece_type] + pst_value
        if piece.piece_type == chess.PAWN:
            king_square = b.king(piece.color)
            if king_square and chess.square_distance(square, king_square) <= 2: piece_value += pawn_shield_value
            is_passed = True
            for test_file in range(max(0, chess.square_file(square)-1), min(7, chess.square_file(square)+1) + 1):
                for test_rank in range(chess.square_rank(square) + (1 if piece.color == chess.WHITE else -1), 8 if piece.color == chess.WHITE else -1, 1 if piece.color == chess.WHITE else -1):
                    p = b.piece_at(chess.square(test_file, test_rank))
                    if p and p.piece_type == chess.PAWN and p.color != piece.color:
                        is_passed = False; break
                if not is_passed: break
            if is_passed:
                rank = chess.square_rank(square) if piece.color == chess.WHITE else 7 - chess.square_rank(square)
                piece_value += passed_pawn_bonus[rank]
        elif piece.piece_type == chess.ROOK:
            file_has_friendly_pawn = False
            file_has_enemy_pawn = False
            for rank in range(8):
                p = b.piece_at(chess.square(chess.square_file(square), rank))
                if p and p.piece_type == chess.PAWN:
                    if p.color == piece.color: file_has_friendly_pawn = True
                    else: file_has_enemy_pawn = True
            if not file_has_friendly_pawn:
                if not file_has_enemy_pawn: piece_value += ROOK_OPEN_FILE_BONUS
                else: piece_value += ROOK_SEMI_OPEN_FILE_BONUS
        t_eval += piece_value if piece.color == chess.WHITE else -piece_value
    mobility = len(list(b.legal_moves))
    if b.turn == chess.WHITE: t_eval += mobility * MOBILITY_BONUS_PER_MOVE
    else: t_eval -= mobility * MOBILITY_BONUS_PER_MOVE
    return t_eval

def get_move_score(board, move):
    score = 0
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if victim and attacker: score = 10 * piece_values.get(victim.piece_type, 0) - piece_values.get(attacker.piece_type, 0)
    return score

def quiescence_search(board, alpha, beta, stop_event):
    if stop_event.is_set(): return TIME_UP_FLAG
    stand_pat = evaluate_board(board)
    if board.turn == chess.WHITE:
        if stand_pat >= beta: return beta
        alpha = max(alpha, stand_pat)
    else:
        if stand_pat <= alpha: return alpha
        beta = min(beta, stand_pat)
    capture_moves = sorted([m for m in board.legal_moves if board.is_capture(m)], key=lambda m: get_move_score(board, m), reverse=True)
    for move in capture_moves:
        if stop_event.is_set(): return TIME_UP_FLAG
        board.push(move)
        score = quiescence_search(board, alpha, beta, stop_event)
        board.pop()
        if score == TIME_UP_FLAG: return TIME_UP_FLAG
        if board.turn == chess.WHITE:
            alpha = max(alpha, score)
            if alpha >= beta: break
        else:
            beta = min(beta, score)
            if beta <= alpha: break
    return alpha if board.turn == chess.WHITE else beta

def minimax(board, depth, alpha, beta, maximizing_player, transposition_table, stop_event, best_move_from_prev_iter=None):
    if stop_event.is_set(): return TIME_UP_FLAG, None
    original_alpha = alpha
    zobrist_key = chess.polyglot.zobrist_hash(board)
    if zobrist_key in transposition_table:
        entry = transposition_table[zobrist_key]
        if entry['depth'] >= depth:
            if entry['flag'] == EXACT_FLAG: return entry['score'], entry.get('move')
            elif entry['flag'] == LOWERBOUND_FLAG: alpha = max(alpha, entry['score'])
            elif entry['flag'] == UPPERBOUND_FLAG: beta = min(beta, entry['score'])
            if alpha >= beta: return entry['score'], entry.get('move')
    if depth == 0 or board.is_game_over(claim_draw=True):
        return quiescence_search(board, alpha, beta, stop_event), None
    moves = sorted(list(board.legal_moves), key=lambda move: get_move_score(board, move), reverse=True)
    if best_move_from_prev_iter and best_move_from_prev_iter in moves:
        moves.insert(0, moves.pop(moves.index(best_move_from_prev_iter)))
    best_move = None
    if maximizing_player:
        max_eval = -float('inf')
        for move in moves:
            if stop_event.is_set(): return TIME_UP_FLAG, None
            board.push(move)
            eval, _ = minimax(board, depth - 1, alpha, beta, False, transposition_table, stop_event)
            board.pop()
            if eval == TIME_UP_FLAG: return TIME_UP_FLAG, None
            if eval > max_eval: max_eval = eval; best_move = move
            alpha = max(alpha, eval)
            if beta <= alpha: break
        entry = {'score': max_eval, 'depth': depth, 'move': best_move}
        if max_eval <= original_alpha: entry['flag'] = UPPERBOUND_FLAG
        elif max_eval >= beta: entry['flag'] = LOWERBOUND_FLAG
        else: entry['flag'] = EXACT_FLAG
        transposition_table[zobrist_key] = entry
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for move in moves:
            if stop_event.is_set(): return TIME_UP_FLAG, None
            board.push(move)
            eval, _ = minimax(board, depth - 1, alpha, beta, True, transposition_table, stop_event)
            board.pop()
            if eval == TIME_UP_FLAG: return TIME_UP_FLAG, None
            if eval < min_eval: min_eval = eval; best_move = move
            beta = min(beta, eval)
            if beta <= alpha: break
        entry = {'score': min_eval, 'depth': depth, 'move': best_move}
        if min_eval <= original_alpha: entry['flag'] = UPPERBOUND_FLAG
        elif min_eval >= beta: entry['flag'] = LOWERBOUND_FLAG
        else: entry['flag'] = EXACT_FLAG
        transposition_table[zobrist_key] = entry
        return min_eval, best_move

def iterative_deepening_search(board, maximizing_player, transposition_table, stop_event):
    best_move_so_far = None
    for depth in range(1, 100):
        if stop_event.is_set():
            print(f"Time is up. Best move from depth {depth-1}."); break
        print(f"Searching at depth {depth}...")
        score, move = minimax(board, depth, -float('inf'), float('inf'), maximizing_player, transposition_table, stop_event, best_move_so_far)
        if score == TIME_UP_FLAG:
            print(f"Time ran out during depth {depth}. Using previous result."); break
        if move: best_move_so_far = move
    if best_move_so_far is None:
        print("No move found within time limit, picking a random legal move.")
        legal_moves = list(board.legal_moves)
        if legal_moves: best_move_so_far = random.choice(legal_moves)
    return best_move_so_far

def get_ai_move_threaded_worker(board_fen, time_limit, maximizing_player, result_queue, transposition_table, stop_event):
    timer = threading.Timer(time_limit, stop_event.set)
    timer.start()
    thread_board = chess.Board(board_fen)
    best_move = iterative_deepening_search(thread_board, maximizing_player, transposition_table, stop_event)
    timer.cancel()
    if not stop_event.is_set(): stop_event.set()
    result_queue.put(best_move)
# --- [ END OF AI CODE ] ---

# --- Global Asset & Layout Variables ---
CONFIG = {}
SQUARE_SIZE, COORDINATE_AREA_SIZE, CAPTURED_AREA_HEIGHT = 0, 0, 0
CAPTURED_PIECE_DISPLAY_SIZE, MOVE_HISTORY_WIDTH, MOVE_HISTORY_FONT_SIZE = 0, 0, 0
MOVE_HISTORY_LINE_HEIGHT, INFO_PANEL_HEIGHT, BUTTON_AREA_HEIGHT = 0, 0, 0
BUTTON_FONT_SIZE, BUTTON_PADDING, NEW_GAME_BUTTON_WIDTH, ACTION_BUTTON_WIDTH, BUTTON_HEIGHT = 0, 0, 0, 0, 0
PROMOTION_CHOICE_IMG_SIZE, PROMOTION_CHOICE_HEIGHT = 0, 0
BOARD_DRAW_WIDTH, BOARD_DRAW_HEIGHT, Y_POS_TOP_PADDING = 0, 0, 0
Y_POS_TOP_CAPTURED_AREA, Y_POS_TOP_COORDS, BOARD_OFFSET_Y = 0, 0, 0
Y_POS_BOTTOM_COORDS, Y_POS_BOTTOM_CAPTURED_AREA, Y_POS_INFO_PANEL = 0, 0, 0
Y_POS_BUTTON_AREA, Y_POS_BOTTOM_PADDING, SCREEN_HEIGHT = 0, 0, 0
BOARD_OFFSET_X, X_POS_MOVE_HISTORY, SCREEN_WIDTH = 0, 0, 0
LIFTED_PIECE_SCALE, LIFTED_PIECE_SIZE = 0, 0
CENTRAL_COLUMN_WIDTH, CENTRAL_COLUMN_X_START = 0, 0
EVAL_BAR_WIDTH, EVAL_BAR_PADDING_X, X_POS_EVAL_BAR, EVAL_BAR_Y = 0, 0, 0, 0
PIECE_IMAGES, LIFTED_PIECE_IMAGES, CAPTURED_DISPLAY_PIECE_IMAGES = {}, {}, {}
PROMOTION_PIECE_IMAGES, SOUNDS, SPINNER_FRAMES = {}, {}, []
INFO_FONT, MOVE_HISTORY_FONT, BUTTON_FONT, COORD_FONT, GAME_OVER_FONT, OVERLAY_FONT = None, None, None, None, None, None
PROMOTION_TYPES = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]

def initialize_game(config_filename="config.json"):
    global CONFIG, SQUARE_SIZE, COORDINATE_AREA_SIZE, CAPTURED_AREA_HEIGHT, CAPTURED_PIECE_DISPLAY_SIZE
    global MOVE_HISTORY_WIDTH, MOVE_HISTORY_FONT_SIZE, MOVE_HISTORY_LINE_HEIGHT, INFO_PANEL_HEIGHT, BUTTON_AREA_HEIGHT
    global BUTTON_FONT_SIZE, BUTTON_PADDING, NEW_GAME_BUTTON_WIDTH, ACTION_BUTTON_WIDTH, BUTTON_HEIGHT
    global PROMOTION_CHOICE_IMG_SIZE, PROMOTION_CHOICE_HEIGHT, BOARD_DRAW_WIDTH, BOARD_DRAW_HEIGHT, Y_POS_TOP_PADDING
    global Y_POS_TOP_CAPTURED_AREA, Y_POS_TOP_COORDS, BOARD_OFFSET_Y, Y_POS_BOTTOM_COORDS, Y_POS_BOTTOM_CAPTURED_AREA
    global Y_POS_INFO_PANEL, Y_POS_BUTTON_AREA, Y_POS_BOTTOM_PADDING, SCREEN_HEIGHT, BOARD_OFFSET_X, X_POS_MOVE_HISTORY
    global SCREEN_WIDTH, LIFTED_PIECE_SCALE, LIFTED_PIECE_SIZE, CENTRAL_COLUMN_WIDTH, CENTRAL_COLUMN_X_START
    global EVAL_BAR_WIDTH, EVAL_BAR_PADDING_X, X_POS_EVAL_BAR, EVAL_BAR_Y
    try:
        with open(config_filename, 'r') as f: CONFIG = json.load(f)
        print("Configuration loaded successfully.")
    except (FileNotFoundError, json.JSONDecodeError) as e: print(f"FATAL: Error with '{config_filename}': {e}. Cannot start."); sys.exit(1)
    layout = CONFIG['layout']; eval_bar = CONFIG.get('evaluation_bar', {'width': 20, 'padding_x': 10}); fonts = CONFIG['fonts']
    SQUARE_SIZE = layout['square_size']; COORDINATE_AREA_SIZE = layout['coordinate_area_size']; CAPTURED_AREA_HEIGHT = SQUARE_SIZE * layout['captured_area_height_scale']; CAPTURED_PIECE_DISPLAY_SIZE = int(SQUARE_SIZE * 0.55)
    MOVE_HISTORY_WIDTH = layout['move_history_width']; INFO_PANEL_HEIGHT = layout['info_panel_height']; BUTTON_AREA_HEIGHT = layout['button_area_height']; BUTTON_PADDING = layout['button_padding']
    NEW_GAME_BUTTON_WIDTH = layout['new_game_button_width']; ACTION_BUTTON_WIDTH = layout['action_button_width']; BUTTON_HEIGHT = layout['button_height']
    PROMOTION_CHOICE_IMG_SIZE = int(SQUARE_SIZE * layout['promotion_choice_scale']); PROMOTION_CHOICE_HEIGHT = PROMOTION_CHOICE_IMG_SIZE + 30
    LIFTED_PIECE_SCALE = layout['lifted_piece_scale']; LIFTED_PIECE_SIZE = int(SQUARE_SIZE * LIFTED_PIECE_SCALE)
    MOVE_HISTORY_LINE_HEIGHT = fonts['move_history_line_height']; MOVE_HISTORY_FONT_SIZE = fonts['move_history_font_size']; BUTTON_FONT_SIZE = fonts['button_font_size']
    BOARD_DRAW_WIDTH = 8 * SQUARE_SIZE; BOARD_DRAW_HEIGHT = 8 * SQUARE_SIZE
    Y_POS_TOP_PADDING = 10; Y_POS_TOP_CAPTURED_AREA = Y_POS_TOP_PADDING; Y_POS_TOP_COORDS = Y_POS_TOP_CAPTURED_AREA + int(CAPTURED_AREA_HEIGHT)
    BOARD_OFFSET_Y = Y_POS_TOP_COORDS + COORDINATE_AREA_SIZE; Y_POS_BOTTOM_COORDS = BOARD_OFFSET_Y + BOARD_DRAW_HEIGHT
    Y_POS_BOTTOM_CAPTURED_AREA = Y_POS_BOTTOM_COORDS + COORDINATE_AREA_SIZE; Y_POS_INFO_PANEL = Y_POS_BOTTOM_CAPTURED_AREA + int(CAPTURED_AREA_HEIGHT)
    Y_POS_BUTTON_AREA = Y_POS_INFO_PANEL + INFO_PANEL_HEIGHT; Y_POS_BOTTOM_PADDING = 10 
    SCREEN_HEIGHT = Y_POS_BUTTON_AREA + BUTTON_AREA_HEIGHT + Y_POS_BOTTOM_PADDING
    BOARD_OFFSET_X = COORDINATE_AREA_SIZE 
    EVAL_BAR_WIDTH = eval_bar['width']; EVAL_BAR_PADDING_X = eval_bar['padding_x']; EVAL_BAR_Y = BOARD_OFFSET_Y
    X_POS_EVAL_BAR = BOARD_OFFSET_X + BOARD_DRAW_WIDTH + COORDINATE_AREA_SIZE + EVAL_BAR_PADDING_X
    X_POS_MOVE_HISTORY = X_POS_EVAL_BAR + EVAL_BAR_WIDTH + EVAL_BAR_PADDING_X
    SCREEN_WIDTH = X_POS_MOVE_HISTORY + MOVE_HISTORY_WIDTH + COORDINATE_AREA_SIZE
    CENTRAL_COLUMN_WIDTH = BOARD_DRAW_WIDTH + COORDINATE_AREA_SIZE * 2; CENTRAL_COLUMN_X_START = BOARD_OFFSET_X - COORDINATE_AREA_SIZE

def load_assets():
    global PIECE_IMAGES, LIFTED_PIECE_IMAGES, CAPTURED_DISPLAY_PIECE_IMAGES, PROMOTION_PIECE_IMAGES, SOUNDS
    global INFO_FONT, MOVE_HISTORY_FONT, BUTTON_FONT, COORD_FONT, GAME_OVER_FONT, SPINNER_FRAMES, OVERLAY_FONT
    cfg_font=CONFIG['fonts']; cfg_assets=CONFIG['assets']; cfg_spinner=CONFIG['spinner']
    font_path=os.path.join(cfg_font['custom_font_path'], cfg_font['custom_font_filename']) if cfg_font.get('custom_font_filename') else None
    if font_path and not os.path.exists(font_path): print(f"Font '{font_path}' not found. Using default."); font_path=None
    try:
        INFO_FONT=pygame.font.Font(font_path, cfg_font['info_font_size']); MOVE_HISTORY_FONT=pygame.font.Font(font_path, cfg_font['move_history_font_size']); BUTTON_FONT=pygame.font.Font(font_path, cfg_font['button_font_size'])
        COORD_FONT=pygame.font.Font(font_path, int(COORDINATE_AREA_SIZE * cfg_font['coord_font_size_scale'])); GAME_OVER_FONT=pygame.font.Font(font_path, cfg_font['game_over_font_size']); OVERLAY_FONT=pygame.font.Font(font_path, cfg_font['info_font_size']) 
        print(f"Loaded font: {'Default' if not font_path else cfg_font['custom_font_filename']}")
    except pygame.error as e: print(f"Error loading font: {e}. Using default."); INFO_FONT=pygame.font.Font(None, cfg_font['info_font_size']); MOVE_HISTORY_FONT=pygame.font.Font(None, cfg_font['move_history_font_size']); BUTTON_FONT=pygame.font.Font(None, cfg_font['button_font_size']); COORD_FONT=pygame.font.Font(None, int(COORDINATE_AREA_SIZE*cfg_font['coord_font_size_scale'])); GAME_OVER_FONT=pygame.font.Font(None, cfg_font['game_over_font_size']); OVERLAY_FONT=pygame.font.Font(None, cfg_font['info_font_size'])
    s_map={'P':'wP','N':'wKN','B':'wB','R':'wR','Q':'wQ','K':'wKI','p':'bP','n':'bKN','b':'bB','r':'bR','q':'bQ','k':'bKI'}
    for ps, fb in s_map.items():
        try: 
            fn=os.path.join(cfg_assets['image_path'], f"{fb}.png"); oi=pygame.image.load(fn).convert_alpha()
            PIECE_IMAGES[ps]=pygame.transform.scale(oi,(SQUARE_SIZE,SQUARE_SIZE)); LIFTED_PIECE_IMAGES[ps]=pygame.transform.scale(oi,(LIFTED_PIECE_SIZE, LIFTED_PIECE_SIZE)); CAPTURED_DISPLAY_PIECE_IMAGES[ps]=pygame.transform.scale(oi,(CAPTURED_PIECE_DISPLAY_SIZE, CAPTURED_PIECE_DISPLAY_SIZE))
            if ps.upper() in ['Q','R','B','N']: PROMOTION_PIECE_IMAGES[ps] = pygame.transform.scale(oi,(PROMOTION_CHOICE_IMG_SIZE, PROMOTION_CHOICE_IMG_SIZE))
        except pygame.error as e: print(f"Err Ld Img {fn}: {e}")
    if not pygame.mixer.get_init(): pygame.mixer.init()
    sound_files={"move":"move.wav","capture":"capture.wav","check":"check.wav","game_end":"game_end.wav", "button_click":"button.wav", "illegal":cfg_assets.get('illegal_move_sound',"illegal.wav")}
    for name, file in sound_files.items():
        try: SOUNDS[name] = pygame.mixer.Sound(os.path.join(cfg_assets['sound_path'], file))
        except (pygame.error, FileNotFoundError) as e: print(f"Warning: Sound '{file}' not loaded: {e}"); SOUNDS[name] = None
    if cfg_assets.get('spinner_spritesheet_filename'):
        try:
            sheet=pygame.image.load(os.path.join(cfg_assets['image_path'],cfg_assets['spinner_spritesheet_filename'])).convert_alpha()
            w,h,n=cfg_spinner['frame_width'],cfg_spinner['frame_height'],cfg_spinner['number_of_frames']
            size=(int(w*cfg_spinner['display_scale']),int(h*cfg_spinner['display_scale']))
            for i in range(n): rect=pygame.Rect(i*w,0,w,h); surf=pygame.Surface(rect.size,pygame.SRCALPHA); surf.blit(sheet,(0,0),rect); SPINNER_FRAMES.append(pygame.transform.scale(surf,size))
            print(f"Loaded {len(SPINNER_FRAMES)} spinner frames.")
        except Exception as e: print(f"Error loading spinner: {e}")

def play_sound(name):
    if name in SOUNDS and SOUNDS[name]: SOUNDS[name].play()

def draw_text_wrapped(surface,text,font,color,rect,aa=False,bkg=None):
    rect=pygame.Rect(rect);y=rect.top;line_spacing=2;font_height=font.size("Tg")[1];lines=[]
    while text:
        i=1
        while font.size(text[:i])[0]<rect.width and i<len(text):i+=1
        if i<len(text):i=text.rfind(" ",0,i)+1
        lines.append(text[:i]);text=text[i:]
    total_text_height=len(lines)*(font_height+line_spacing)-line_spacing;y=rect.top+(rect.height-total_text_height)//2
    for line in lines:
        if y+font_height>rect.bottom:break
        image=font.render(line,aa,color);line_rect=image.get_rect(centerx=rect.centerx,top=y);surface.blit(image,line_rect);y+=font_height+line_spacing

class BoardGUI:
    def __init__(self, screen, human_is_white_player):
        self.screen=screen; self.human_is_white_player=human_is_white_player; self.coord_font=COORD_FONT
    def get_pygame_coords(self,sq_idx):
        f,r=chess.square_file(sq_idx),chess.square_rank(sq_idx)
        if self.human_is_white_player: return BOARD_OFFSET_X+f*SQUARE_SIZE, BOARD_OFFSET_Y+(7-r)*SQUARE_SIZE
        else: return BOARD_OFFSET_X+(7-f)*SQUARE_SIZE, BOARD_OFFSET_Y+r*SQUARE_SIZE
    def get_square_from_mouse(self,pos):
        x,y=pos; bx,by=x-BOARD_OFFSET_X, y-BOARD_OFFSET_Y
        if not(0<=bx<BOARD_DRAW_WIDTH and 0<=by<BOARD_DRAW_HEIGHT): return None
        f,r=bx//SQUARE_SIZE, by//SQUARE_SIZE; f_chess=f if self.human_is_white_player else 7-f; r_chess=(7-r) if self.human_is_white_player else r
        if not(0<=f_chess<8 and 0<=r_chess<8): return None
        return chess.square(f_chess, r_chess)
    def draw_board_squares(self):
        C=CONFIG['colors']
        for r in range(8):
            for f in range(8): pygame.draw.rect(self.screen, C['white_square'] if (r+f)%2==0 else C['green_square'], pygame.Rect(BOARD_OFFSET_X+f*SQUARE_SIZE, BOARD_OFFSET_Y+r*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    def draw_coordinates(self):
        C=CONFIG['colors']; files="abcdefgh"; ranks="12345678"
        disp_f, disp_r = files, ranks[::-1] if self.human_is_white_player else ranks
        for i,char in enumerate(disp_f):
            surf=self.coord_font.render(char,True,C['dark_bg_text']); self.screen.blit(surf,surf.get_rect(center=(BOARD_OFFSET_X+i*SQUARE_SIZE+SQUARE_SIZE//2,Y_POS_BOTTOM_COORDS+COORDINATE_AREA_SIZE//2)))
            self.screen.blit(surf,surf.get_rect(center=(BOARD_OFFSET_X+i*SQUARE_SIZE+SQUARE_SIZE//2,Y_POS_TOP_COORDS-COORDINATE_AREA_SIZE//2)))
        for i,char in enumerate(disp_r):
            surf=self.coord_font.render(char,True,C['dark_bg_text']); self.screen.blit(surf,surf.get_rect(center=(BOARD_OFFSET_X-COORDINATE_AREA_SIZE//2,BOARD_OFFSET_Y+i*SQUARE_SIZE+SQUARE_SIZE//2)))
            self.screen.blit(surf,surf.get_rect(center=(BOARD_OFFSET_X+BOARD_DRAW_WIDTH+COORDINATE_AREA_SIZE//2,BOARD_OFFSET_Y+i*SQUARE_SIZE+SQUARE_SIZE//2)))
    def draw_last_move_highlight(self,move):
        if move:
            for sq in [move.from_square,move.to_square]: x,y=self.get_pygame_coords(sq); hs=pygame.Surface((SQUARE_SIZE,SQUARE_SIZE),pygame.SRCALPHA); hs.fill(CONFIG['colors']['last_move']); self.screen.blit(hs,(x,y))
    def draw_check_highlight(self,board):
        if board.is_check():
            ksq=board.king(board.turn);
            if ksq is not None: x,y=self.get_pygame_coords(ksq); hs=pygame.Surface((SQUARE_SIZE,SQUARE_SIZE),pygame.SRCALPHA); hs.fill(CONFIG['colors']['check']); self.screen.blit(hs,(x,y))
    def draw_pieces(self,board,sel,drag):
        for i in range(64):
            if i==sel and drag: continue
            if board.piece_at(i): self.screen.blit(PIECE_IMAGES[board.piece_at(i).symbol()], self.get_pygame_coords(i))
    def draw_selected_and_legal_moves_highlights(self,board,sel):
        if sel is not None:
            C=CONFIG['colors']; x,y=self.get_pygame_coords(sel); shs=pygame.Surface((SQUARE_SIZE,SQUARE_SIZE),pygame.SRCALPHA); shs.fill(C['selected_square']); self.screen.blit(shs,(x,y))
            for move in board.legal_moves:
                if move.from_square == sel:
                    tsx,tsy=self.get_pygame_coords(move.to_square); mhs=pygame.Surface((SQUARE_SIZE,SQUARE_SIZE),pygame.SRCALPHA)
                    if board.is_capture(move): pygame.draw.circle(mhs,C['capture_ring'],(SQUARE_SIZE//2,SQUARE_SIZE//2),SQUARE_SIZE//2-3,4) 
                    else: pygame.draw.circle(mhs,C['legal_move'],(SQUARE_SIZE//2,SQUARE_SIZE//2),SQUARE_SIZE//5)
                    self.screen.blit(mhs,(tsx,tsy))
    def draw_captured_pieces(self,syms,top):
        y=Y_POS_TOP_CAPTURED_AREA if top else Y_POS_BOTTOM_CAPTURED_AREA; pygame.draw.rect(self.screen,CONFIG['colors']['captured_area_bg'],(BOARD_OFFSET_X,y,BOARD_DRAW_WIDTH,int(CAPTURED_AREA_HEIGHT)))
        x=BOARD_OFFSET_X+5; dy=y+(int(CAPTURED_AREA_HEIGHT)-CAPTURED_PIECE_DISPLAY_SIZE)//2
        for s in syms:
            if s in CAPTURED_DISPLAY_PIECE_IMAGES:
                if x+CAPTURED_PIECE_DISPLAY_SIZE>BOARD_OFFSET_X+BOARD_DRAW_WIDTH-5: break 
                self.screen.blit(CAPTURED_DISPLAY_PIECE_IMAGES[s],(x,dy)); x+=CAPTURED_PIECE_DISPLAY_SIZE+3
    def draw_promotion_choice(self,color,mouse_pos):
        C=CONFIG['colors']; w=PROMOTION_CHOICE_IMG_SIZE*4+10*5; h=PROMOTION_CHOICE_HEIGHT; x=BOARD_OFFSET_X+(BOARD_DRAW_WIDTH-w)//2; y=BOARD_OFFSET_Y+(BOARD_DRAW_HEIGHT-h)//2 
        dim=pygame.Surface(self.screen.get_size(),pygame.SRCALPHA); dim.fill((0,0,0,100)); self.screen.blit(dim,(0,0))
        pygame.draw.rect(self.screen,C['promotion_bg'],(x,y,w,h)); pygame.draw.rect(self.screen,C['promotion_border'],(x,y,w,h),3)
        rects=[]; cx=x+10
        for p_type in PROMOTION_TYPES:
            key=chess.piece_symbol(p_type).upper() if color==chess.WHITE else chess.piece_symbol(p_type).lower()
            if key in PROMOTION_PIECE_IMAGES:
                img=PROMOTION_PIECE_IMAGES[key]; img_y=y+(h-PROMOTION_CHOICE_IMG_SIZE)//2; img_rect=img.get_rect(topleft=(cx,img_y))
                if img_rect.collidepoint(mouse_pos): pygame.draw.rect(self.screen,C['promotion_hover_bg'],img_rect.inflate(6,6),border_radius=3)
                self.screen.blit(img,img_rect); rects.append((img_rect,p_type)); cx+=PROMOTION_CHOICE_IMG_SIZE+10
        return rects
    def draw_move_history(self,hist,font):
        C=CONFIG['colors']; hx=X_POS_MOVE_HISTORY; hy=BOARD_OFFSET_Y; hh=BOARD_DRAW_HEIGHT
        pygame.draw.rect(self.screen,C['move_history_bg'],(hx,hy,MOVE_HISTORY_WIDTH,hh)); pygame.draw.rect(self.screen,C['promotion_border'],(hx,hy,MOVE_HISTORY_WIDTH,hh),2)
        yo=hy+5; max_moves=(hh-10)//MOVE_HISTORY_LINE_HEIGHT; start_idx=max(0,len(hist)-max_moves*2)
        if start_idx%2!=0: start_idx-=1
        move_num=(start_idx//2)+1
        for i in range(start_idx,len(hist),2):
            if yo>hy+hh-MOVE_HISTORY_LINE_HEIGHT-5: break 
            w=hist[i] if i<len(hist) else ""; b=hist[i+1] if i+1<len(hist) else ""
            line=f"{move_num}. {w:<7} {b:<7}"; surf=font.render(line,True,C['white_text']); self.screen.blit(surf,(hx+5,yo)); yo+=MOVE_HISTORY_LINE_HEIGHT; move_num+=1
    def draw_button(self,txt,x,y,w,h,font,pressed=False,enabled=True):
        C=CONFIG['colors']; rect=pygame.Rect(x,y,w,h); hovered=rect.collidepoint(pygame.mouse.get_pos()) and enabled
        bg=C['button_pressed_bg'] if pressed else (C['button_hover_bg'] if hovered else C['button_bg']); txt_color=C['button_text']
        if not enabled: bg=(50,50,50); txt_color=(120,120,120)
        pygame.draw.rect(self.screen,bg,rect); pygame.draw.rect(self.screen,C['button_border'],rect,2)
        offset=2 if pressed and enabled else 0
        surf=font.render(txt,True,txt_color); self.screen.blit(surf,surf.get_rect(center=(rect.centerx,rect.centery+offset)))
        return rect
    def draw_settings_button(self,text,rect,is_selected):
        C=CONFIG['colors']; hovered=rect.collidepoint(pygame.mouse.get_pos())
        bg=C['settings_button_selected_bg'] if is_selected else (C['settings_button_hover'] if hovered else C['settings_button'])
        pygame.draw.rect(self.screen,bg,rect,border_radius=5)
        text_surf=BUTTON_FONT.render(text,True,C['settings_text']); self.screen.blit(text_surf,text_surf.get_rect(center=rect.center))

class Game:
    def __init__(self, screen):
        self.screen=screen; self.game_state="SETTINGS"
        self.temp_human_is_white=True; self.temp_search_time=CONFIG['ai']['difficulty']['medium']['time_seconds']
        self.human_is_white=True; self.search_time=self.temp_search_time
        self.board_gui=BoardGUI(screen, self.human_is_white)
        self.button_pressed_state={}; self.ai_is_actively_thinking=False; self.stop_search_event=None
        self.ai_thread=None; self.ai_move_queue=queue.Queue()
        self.hint_thread=None; self.hint_queue=queue.Queue()
        self.human_offered_draw=False; self.ai_offered_draw=False; self.player_mode="HUMAN_VS_AI"
        self.transposition_table={}
        try:
            book_path=CONFIG['assets']['opening_book_path']
            self.opening_book=chess.polyglot.open_reader(book_path)
            print(f"Opening book '{book_path}' loaded.")
        except (FileNotFoundError,IOError) as e:
            print(f"Warning: Opening book not found: {e}. AI will not use one."); self.opening_book=None
        self._reset_game_state_vars()
    def _reset_game_state_vars(self):
        self.board=chess.Board(); self.is_ai_player_white=not self.human_is_white; self.selected_square_idx=None; self.last_played_move=None
        self.game_is_over=False; self.captured_by_white=[]; self.captured_by_black=[]; self.move_history_san=[]
        self.board_move_stack_for_undo=[]; self.awaiting_promotion=False; self.promotion_move_from=None; self.promotion_move_to=None; self.promotion_choice_rects=[]
        self.dragging_piece_img=None; self.dragging_piece_original_square=None; self.ai_is_actively_thinking=False; self.ai_thread=None
        self.ai_move_queue=queue.Queue(); self.hint_thread=None; self.hint_queue=queue.Queue(); self.hint_move=None; self.hint_display_until=0
        self.human_offered_draw=False; self.ai_offered_draw=False; self.ai_response_message=""; self.ai_response_message_until=0
        self.resignation_winner=None; self.draw_by_agreement=False; self.game_over_time=0; self.current_eval_score=0.0
        self.pending_ai_move=None; self.ai_turn_start_time=0; self.aivsai_delay_until=0; self.transposition_table.clear()
        self._update_status_message()
    def _get_game_settings_gui(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1: return
        pos = event.pos
        if self.player_mode_btn_rect.collidepoint(pos): self.player_mode="AI_VS_AI" if self.player_mode=="HUMAN_VS_AI" else "HUMAN_VS_AI"; play_sound("button_click")
        elif self.player_mode=="HUMAN_VS_AI" and self.side_btn_rect.collidepoint(pos): self.temp_human_is_white=not self.temp_human_is_white; play_sound("button_click")
        elif self.easy_button_rect.collidepoint(pos): self.temp_search_time=CONFIG['ai']['difficulty']['easy']['time_seconds']; play_sound("button_click")
        elif self.medium_button_rect.collidepoint(pos): self.temp_search_time=CONFIG['ai']['difficulty']['medium']['time_seconds']; play_sound("button_click")
        elif self.hard_button_rect.collidepoint(pos): self.temp_search_time=CONFIG['ai']['difficulty']['hard']['time_seconds']; play_sound("button_click")
        elif self.start_button_rect.collidepoint(pos):
            self.human_is_white=self.temp_human_is_white; self.search_time=self.temp_search_time
            perspective=self.human_is_white if self.player_mode=="HUMAN_VS_AI" else True
            if self.board_gui is None or self.board_gui.human_is_white_player!=perspective: self.board_gui=BoardGUI(self.screen, perspective)
            self._reset_game_state_vars(); self.game_state="PLAYING"; play_sound("button_click")
    def _draw_settings_screen(self):
        C=CONFIG['colors']; self.screen.fill(C['settings_bg'])
        panel_w,panel_h=600,450; panel_rect=pygame.Rect((SCREEN_WIDTH-panel_w)/2,(SCREEN_HEIGHT-panel_h)/2,panel_w,panel_h)
        pygame.draw.rect(self.screen,C['settings_panel_bg'],panel_rect,border_radius=10); pygame.draw.rect(self.screen,C['settings_panel_border'],panel_rect,3,border_radius=10)
        title_surf=GAME_OVER_FONT.render("Chess AI",True,C['settings_text']); self.screen.blit(title_surf,title_surf.get_rect(centerx=panel_rect.centerx,y=panel_rect.y+20))
        def draw_section(title,y): text_surf=INFO_FONT.render(title,True,C['settings_text']); self.screen.blit(text_surf,text_surf.get_rect(left=panel_rect.left+30,y=panel_rect.y+y))
        btn_w,btn_h,btn_pad=180,45,10
        draw_section("Game Mode",90); mode_y=panel_rect.y+130
        self.player_mode_btn_rect=pygame.Rect(panel_rect.centerx-btn_w/2,mode_y,btn_w,btn_h)
        self.board_gui.draw_settings_button("Human vs AI" if self.player_mode=="HUMAN_VS_AI" else "AI vs AI",self.player_mode_btn_rect,True)
        if self.player_mode=="HUMAN_VS_AI":
            draw_section("Your Side",190); side_y=panel_rect.y+230
            self.side_btn_rect=pygame.Rect(panel_rect.centerx-btn_w/2,side_y,btn_w,btn_h)
            self.board_gui.draw_settings_button("White" if self.temp_human_is_white else "Black",self.side_btn_rect,True)
        difficulty_y_offset = 290 if self.player_mode == "HUMAN_VS_AI" else 190
        draw_section("Difficulty", difficulty_y_offset)
        diff_y = panel_rect.y + difficulty_y_offset + 40
        easy_t,med_t,hard_t=CONFIG['ai']['difficulty']['easy']['time_seconds'],CONFIG['ai']['difficulty']['medium']['time_seconds'],CONFIG['ai']['difficulty']['hard']['time_seconds']
        self.easy_button_rect=pygame.Rect(panel_rect.centerx-btn_w*1.5-btn_pad,diff_y,btn_w,btn_h); self.board_gui.draw_settings_button(f"Easy ({easy_t}s)",self.easy_button_rect,self.temp_search_time==easy_t)
        self.medium_button_rect=pygame.Rect(panel_rect.centerx-btn_w/2,diff_y,btn_w,btn_h); self.board_gui.draw_settings_button(f"Medium ({med_t}s)",self.medium_button_rect,self.temp_search_time==med_t)
        self.hard_button_rect=pygame.Rect(panel_rect.centerx+btn_w/2+btn_pad,diff_y,btn_w,btn_h); self.board_gui.draw_settings_button(f"Hard ({hard_t}s)",self.hard_button_rect,self.temp_search_time==hard_t)
        self.start_button_rect=self.board_gui.draw_button("Start Game",panel_rect.centerx-100,panel_rect.bottom-70,200,50,INFO_FONT)
        pygame.display.flip()
    def _reset_game_for_new_game_button(self): self.game_state="SETTINGS"
    def _undo_action_button(self): 
        if not self.awaiting_promotion and not self.ai_is_actively_thinking: self._undo_last_pair_of_moves()
    def _resign_action_button(self):
        if not self.game_is_over: self.game_is_over=True; play_sound("game_end"); self.resignation_winner=chess.BLACK if self.human_is_white else chess.WHITE; self.game_state="GAME_OVER_DISPLAY"; self.game_over_time=pygame.time.get_ticks()
    def _offer_draw_action_button(self):
        if not self.game_is_over and self.is_player_turn_now() and not self.human_offered_draw and not self.ai_offered_draw: self.human_offered_draw=True; self.status_message="Draw offered..."
        elif self.ai_offered_draw: self.game_is_over=True; play_sound("game_end"); self.draw_by_agreement=True; self.ai_offered_draw=False; self.human_offered_draw=False; self.game_state="GAME_OVER_DISPLAY"; self.game_over_time=pygame.time.get_ticks()
    def _get_hint_action(self):
        if self.is_player_turn_now() and not self.game_is_over and not (self.hint_thread and self.hint_thread.is_alive()) and not self.ai_is_actively_thinking:
            self.stop_search_event=threading.Event()
            self.hint_thread=threading.Thread(target=get_ai_move_threaded_worker,args=(self.board.fen(),self.search_time,self.board.turn==chess.WHITE,self.hint_queue,self.transposition_table,self.stop_search_event),daemon=True); self.hint_thread.start()
    def _update_status_message(self):
        if self.ai_is_actively_thinking and not(self.hint_thread and self.hint_thread.is_alive()): self.status_message=f"AI ({'White' if self.board.turn==chess.WHITE else 'Black'}) thinking"
        elif self.ai_response_message and pygame.time.get_ticks()<self.ai_response_message_until: self.status_message=self.ai_response_message
        elif self.awaiting_promotion and self.is_player_turn_now(): self.status_message="Choose promotion piece!"
        elif self.game_is_over:
            if self.resignation_winner is not None: self.status_message=f"{'Black' if self.resignation_winner==chess.BLACK else 'White'} wins by Resignation."
            elif self.draw_by_agreement: self.status_message="Draw by Agreement!"
            else:
                outcome=self.board.outcome()
                if outcome: self.status_message=f"Checkmate! {'Black' if outcome.winner==chess.BLACK else 'White'} Wins!" if outcome.termination==chess.Termination.CHECKMATE else f"Draw: {outcome.termination.name.replace('_',' ').title()}."
                else: self.status_message="Game Over"
        elif self.human_offered_draw: self.status_message="Draw offered..."
        elif self.ai_offered_draw: self.status_message="AI offers a draw. Accept?"
        else: 
            tc="White" if self.board.turn==chess.WHITE else "Black"; cs=" (Check!)" if self.board.is_check() else ""
            if self.player_mode=="AI_VS_AI": self.status_message=f"AI ({tc}) to move..."
            elif self.is_player_turn_now(): self.status_message=f"Your ({tc}) turn{cs}"
            else: self.status_message=f"AI ({tc}) to move..."
        if not self.game_is_over and not self.ai_is_actively_thinking: self.status_message+=f" | Eval: {self.current_eval_score/100:+.2f}"
    def is_player_turn_now(self): return self.player_mode=="HUMAN_VS_AI" and ((self.human_is_white and self.board.turn==chess.WHITE) or (not self.human_is_white and self.board.turn==chess.BLACK))
    def _handle_move_push_and_history(self,move):
        san=self.board.san(move); captured=self.board.piece_at(move.to_square)
        if self.board.is_en_passant(move): captured=chess.Piece(chess.PAWN,not self.board.turn)
        self.board_move_stack_for_undo.append(self.board.fen()); self.board.push(move); self.move_history_san.append(san); self.last_played_move=move
        if captured: (self.captured_by_white if self.board.turn==chess.BLACK else self.captured_by_black).append(captured.symbol())
        play_sound("capture" if captured else "move"); 
        if self.board.is_check(): play_sound("check")
        self.ai_offered_draw=False; self.current_eval_score=evaluate_board(self.board)
        if self.player_mode=="AI_VS_AI": self.aivsai_delay_until=pygame.time.get_ticks()+CONFIG['timing']['ai_vs_ai_move_delay_ms']
    def _undo_last_pair_of_moves(self):
        if self.game_is_over or not self.board.move_stack: return
        num_pops=2 if self.player_mode=="HUMAN_VS_AI" else 1
        if len(self.board.move_stack)<num_pops: return
        for _ in range(num_pops):
            if not self.board.move_stack: break
            fen_before=self.board_move_stack_for_undo.pop() if self.board_move_stack_for_undo else None
            undone_move=self.board.pop()
            if self.move_history_san: self.move_history_san.pop()
            if fen_before:
                board_before=chess.Board(fen_before)
                if board_before.is_capture(undone_move):
                    if board_before.turn==chess.WHITE and self.captured_by_white: self.captured_by_white.pop()
                    elif board_before.turn==chess.BLACK and self.captured_by_black: self.captured_by_black.pop()
        self.last_played_move=self.board.peek() if self.board.move_stack else None
        self.selected_square_idx=None; self.awaiting_promotion=False; self.dragging_piece_img=None; self.game_is_over=False
        self.human_offered_draw=False; self.ai_offered_draw=False; self.resignation_winner=None; self.draw_by_agreement=False
        self.current_eval_score=evaluate_board(self.board); self._update_status_message(); play_sound("move") 
    def handle_input(self,event):
        if self.game_state=="SETTINGS": self._get_game_settings_gui(event); return
        if self.ai_is_actively_thinking and event.type!=pygame.QUIT:
            if event.type==pygame.MOUSEBUTTONUP and self.new_game_button_rect.collidepoint(event.pos):
                play_sound("button_click"); self.stop_search_event.set(); self._reset_game_for_new_game_button()
            return
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            pos=event.pos; buttons={"new_game":self.new_game_button_rect,"undo":self.undo_button_rect,"resign":self.resign_button_rect,"offer_draw":self.offer_draw_button_rect,"hint":self.hint_button_rect}
            for name,rect in buttons.items():
                if rect and rect.collidepoint(pos):
                    is_interactive=not self.ai_is_actively_thinking and not self.game_is_over and not (self.hint_thread and self.hint_thread.is_alive())
                    is_enabled=False
                    if name=="new_game": is_enabled=True
                    elif name=="undo": is_enabled=is_interactive and len(self.board.move_stack)>0 and self.player_mode=="HUMAN_VS_AI"
                    elif name=="resign": is_enabled=is_interactive and self.player_mode=="HUMAN_VS_AI"
                    elif name=="hint": is_enabled=is_interactive and self.is_player_turn_now()
                    elif name=="offer_draw": is_enabled=is_interactive and self.is_player_turn_now() and not self.human_offered_draw
                    if is_enabled: self.button_pressed_state[name]=True
                    return
        if event.type==pygame.MOUSEBUTTONUP and event.button==1:
            pos=event.pos; actions={"new_game":self._reset_game_for_new_game_button,"undo":self._undo_action_button,"resign":self._resign_action_button,"offer_draw":self._offer_draw_action_button,"hint":self._get_hint_action}
            action_taken=False
            for name,action in actions.items():
                rect=getattr(self,f"{name}_button_rect",None)
                if rect and rect.collidepoint(pos) and self.button_pressed_state.get(name):
                    play_sound("button_click"); action(); action_taken=True
            self.button_pressed_state.clear()
            if action_taken: return
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_n: play_sound("button_click"); self._reset_game_for_new_game_button()
            elif event.key==pygame.K_u and self.player_mode=="HUMAN_VS_AI": play_sound("button_click"); self._undo_action_button()
            return
        if self.awaiting_promotion and self.is_player_turn_now():
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                for rect,p_type in self.promotion_choice_rects:
                    if rect.collidepoint(event.pos):
                        play_sound("button_click"); move=chess.Move(self.promotion_move_from,self.promotion_move_to,promotion=p_type)
                        if move in self.board.legal_moves: self._handle_move_push_and_history(move)
                        self.awaiting_promotion=False; self.selected_square_idx=None; self.dragging_piece_img=None; break
        elif not self.game_is_over and self.is_player_turn_now():
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                sq=self.board_gui.get_square_from_mouse(event.pos)
                if sq is not None:
                    piece=self.board.piece_at(sq)
                    if self.selected_square_idx is None and piece and piece.color==self.board.turn:
                        self.selected_square_idx=sq; self.dragging_piece_img=LIFTED_PIECE_IMAGES.get(piece.symbol()); self.dragging_piece_original_square=sq
            elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
                if self.selected_square_idx is not None and self.dragging_piece_img:
                    dropped_sq=self.board_gui.get_square_from_mouse(event.pos)
                    if dropped_sq is not None and dropped_sq!=self.dragging_piece_original_square:
                        is_promo=any(chess.Move(self.selected_square_idx,dropped_sq,promotion=p) in self.board.legal_moves for p in PROMOTION_TYPES)
                        if is_promo: self.awaiting_promotion=True; self.promotion_move_from=self.selected_square_idx; self.promotion_move_to=dropped_sq
                        else:
                            move=chess.Move(self.selected_square_idx,dropped_sq)
                            if move in self.board.legal_moves: self._handle_move_push_and_history(move)
                            else: play_sound("illegal")
                    self.selected_square_idx=None; self.dragging_piece_img=None
    def update_ai(self):
        if pygame.time.get_ticks()<self.aivsai_delay_until: return
        if self.pending_ai_move:
            if pygame.time.get_ticks()-self.ai_turn_start_time>CONFIG['timing']['min_ai_turn_duration_ms']:
                self._handle_move_push_and_history(self.pending_ai_move)
                self.pending_ai_move=None; self.ai_is_actively_thinking=False; pygame.display.set_caption("Chess AI"); self._check_game_over_conditions(); self._update_status_message()
            return
        is_ai_turn=self.player_mode=="AI_VS_AI" or not self.is_player_turn_now()
        if not self.game_is_over and is_ai_turn and not self.awaiting_promotion:
            if self.opening_book and len(self.board.move_stack)<CONFIG['ai']['opening_book_max_moves']:
                try:
                    # --- FIX: Use weighted_choice which is more robust and correct ---
                    entry = self.opening_book.weighted_choice(self.board)
                    if entry: print("AI played from external book."); self.ai_is_actively_thinking=True; self.ai_turn_start_time=pygame.time.get_ticks(); self.pending_ai_move=entry.move; return
                except IndexError: pass # No book move found for this position
            if not self.ai_is_actively_thinking:
                if self.human_offered_draw:
                    current_eval=evaluate_board(self.board); accept_draw=(self.is_ai_player_white and current_eval<=CONFIG['ai']['accept_draw_threshold']) or (not self.is_ai_player_white and current_eval>=-CONFIG['ai']['accept_draw_threshold'])
                    self.human_offered_draw=False
                    if accept_draw: self.game_is_over=True; self.draw_by_agreement=True; self.game_state="GAME_OVER_DISPLAY"; self.game_over_time=pygame.time.get_ticks(); play_sound("game_end"); self._update_status_message(); return
                    else: self.ai_response_message="AI declines the draw."; self.ai_response_message_until=pygame.time.get_ticks()+2000; self._update_status_message(); return
                self.ai_is_actively_thinking=True; self.ai_turn_start_time=pygame.time.get_ticks(); self._update_status_message(); pygame.display.set_caption("Chess AI - AI Thinking...")
                self.stop_search_event=threading.Event()
                self.ai_thread=threading.Thread(target=get_ai_move_threaded_worker,args=(self.board.fen(),self.search_time,self.board.turn==chess.WHITE,self.ai_move_queue,self.transposition_table,self.stop_search_event),daemon=True); self.ai_thread.start()
            try:
                self.pending_ai_move=self.ai_move_queue.get_nowait()
                if not self.pending_ai_move and list(self.board.legal_moves): self.pending_ai_move=random.choice(list(self.board.legal_moves))
                self.ai_thread=None
            except queue.Empty: pass
    def _check_game_over_conditions(self):
        if not self.game_is_over and self.board.is_game_over(claim_draw=True): self.game_is_over=True; play_sound("game_end"); self.game_state="GAME_OVER_DISPLAY"; self.game_over_time=pygame.time.get_ticks()
    def _draw_ai_thinking_overlay(self):
        C=CONFIG['colors']; overlay=pygame.Surface((BOARD_DRAW_WIDTH,BOARD_DRAW_HEIGHT),pygame.SRCALPHA); overlay.fill(C['game_over_overlay']); self.screen.blit(overlay,(BOARD_OFFSET_X,BOARD_OFFSET_Y)) 
        message=f"AI ({'White' if self.board.turn==chess.WHITE else 'Black'}) thinking..."; text_surf=OVERLAY_FONT.render(message,True,C['game_over_text'])
        if SPINNER_FRAMES:
            spinner=SPINNER_FRAMES[pygame.time.get_ticks()//CONFIG['spinner']['animation_speed_ms']%len(SPINNER_FRAMES)]
            total_w=text_surf.get_width()+15+spinner.get_width(); start_x=BOARD_OFFSET_X+(BOARD_DRAW_WIDTH-total_w)/2
            text_y=BOARD_OFFSET_Y+(BOARD_DRAW_HEIGHT-text_surf.get_height())/2
            self.screen.blit(text_surf,(start_x,text_y)); self.screen.blit(spinner,(start_x+text_surf.get_width()+15,text_y+(text_surf.get_height()-spinner.get_height())/2))
        else: draw_text_wrapped(self.screen,message,OVERLAY_FONT,C['game_over_text'],pygame.Rect(BOARD_OFFSET_X+20,BOARD_OFFSET_Y,BOARD_DRAW_WIDTH-40,BOARD_DRAW_HEIGHT),aa=True)
    def draw_buttons(self):
        y=Y_POS_BUTTON_AREA+(BUTTON_AREA_HEIGHT-BUTTON_HEIGHT)//2; total_w=NEW_GAME_BUTTON_WIDTH+(ACTION_BUTTON_WIDTH*4)+(BUTTON_PADDING*4)
        x=CENTRAL_COLUMN_X_START+(CENTRAL_COLUMN_WIDTH-total_w)//2; is_interactive=not self.ai_is_actively_thinking and not self.game_is_over
        self.new_game_button_rect=self.board_gui.draw_button("New Game",x,y,NEW_GAME_BUTTON_WIDTH,BUTTON_HEIGHT,BUTTON_FONT,pressed=self.button_pressed_state.get("new_game"),enabled=True); x+=NEW_GAME_BUTTON_WIDTH+BUTTON_PADDING
        self.undo_button_rect=self.board_gui.draw_button("Undo",x,y,ACTION_BUTTON_WIDTH,BUTTON_HEIGHT,BUTTON_FONT,pressed=self.button_pressed_state.get("undo"),enabled=is_interactive and len(self.board.move_stack)>0 and self.player_mode=="HUMAN_VS_AI"); x+=ACTION_BUTTON_WIDTH+BUTTON_PADDING
        self.resign_button_rect=self.board_gui.draw_button("Resign",x,y,ACTION_BUTTON_WIDTH,BUTTON_HEIGHT,BUTTON_FONT,pressed=self.button_pressed_state.get("resign"),enabled=is_interactive and self.player_mode=="HUMAN_VS_AI"); x+=ACTION_BUTTON_WIDTH+BUTTON_PADDING
        self.offer_draw_button_rect=self.board_gui.draw_button("Draw",x,y,ACTION_BUTTON_WIDTH,BUTTON_HEIGHT,BUTTON_FONT,pressed=self.button_pressed_state.get("offer_draw"),enabled=is_interactive and self.is_player_turn_now() and not self.human_offered_draw); x+=ACTION_BUTTON_WIDTH+BUTTON_PADDING
        self.hint_button_rect=self.board_gui.draw_button("Hint",x,y,ACTION_BUTTON_WIDTH,BUTTON_HEIGHT,BUTTON_FONT,pressed=self.button_pressed_state.get("hint"),enabled=is_interactive and self.is_player_turn_now())
    def _draw_game_over_screen(self):
        C=CONFIG['colors']; overlay=pygame.Surface((BOARD_DRAW_WIDTH,BOARD_DRAW_HEIGHT),pygame.SRCALPHA); overlay.fill(C['game_over_overlay']); self.screen.blit(overlay,(BOARD_OFFSET_X,BOARD_OFFSET_Y)) 
        draw_text_wrapped(self.screen,self.status_message,GAME_OVER_FONT,C['game_over_text'],pygame.Rect(BOARD_OFFSET_X+20,BOARD_OFFSET_Y,BOARD_DRAW_WIDTH-40,BOARD_DRAW_HEIGHT),aa=True)
    def _draw_hint_highlight(self):
        if self.hint_move and pygame.time.get_ticks()<self.hint_display_until:
            for sq in [self.hint_move.from_square,self.hint_move.to_square]:
                x,y=self.board_gui.get_pygame_coords(sq); hs=pygame.Surface((SQUARE_SIZE,SQUARE_SIZE),pygame.SRCALPHA); hs.fill(CONFIG['colors']['hint']); self.screen.blit(hs,(x,y))
        else: self.hint_move=None
    def _draw_evaluation_bar(self):
        C=CONFIG['colors']; max_eval=800; bar_rect=pygame.Rect(X_POS_EVAL_BAR,EVAL_BAR_Y,EVAL_BAR_WIDTH,BOARD_DRAW_HEIGHT)
        clamped_score=max(-max_eval,min(max_eval,self.current_eval_score)); white_prop=(clamped_score+max_eval)/(2*max_eval); white_h=bar_rect.height*white_prop
        white_rect=pygame.Rect(int(bar_rect.x),int(bar_rect.y+(bar_rect.height-white_h)),int(bar_rect.width),int(white_h))
        black_rect=pygame.Rect(int(bar_rect.x),int(bar_rect.y),int(bar_rect.width),int(bar_rect.height-white_h))
        pygame.draw.rect(self.screen,C['white_text'],white_rect); pygame.draw.rect(self.screen,C['dark_bg_text'],black_rect); pygame.draw.rect(self.screen,C['button_border'],bar_rect,2)
    def draw(self):
        if self.game_state=="SETTINGS": self._draw_settings_screen(); return
        self.screen.fill(CONFIG['colors']['screen_bg'])
        self.board_gui.draw_board_squares(); self.board_gui.draw_coordinates(); self._draw_evaluation_bar(); self.board_gui.draw_move_history(self.move_history_san,MOVE_HISTORY_FONT)
        if self.human_is_white: self.board_gui.draw_captured_pieces(self.captured_by_black,True); self.board_gui.draw_captured_pieces(self.captured_by_white,False)
        else: self.board_gui.draw_captured_pieces(self.captured_by_white,True); self.board_gui.draw_captured_pieces(self.captured_by_black,False)
        if not self.game_is_over:
            y=Y_POS_BOTTOM_CAPTURED_AREA if self.is_player_turn_now() else Y_POS_TOP_CAPTURED_AREA
            pygame.draw.rect(self.screen,CONFIG['colors']['turn_indicator_highlight'],(BOARD_OFFSET_X,y,BOARD_DRAW_WIDTH,int(CAPTURED_AREA_HEIGHT)),3)
        self._draw_hint_highlight(); self.board_gui.draw_last_move_highlight(self.last_played_move); self.board_gui.draw_check_highlight(self.board)
        if self.is_player_turn_now() and not self.game_is_over and not self.awaiting_promotion and self.selected_square_idx is not None:
            self.board_gui.draw_selected_and_legal_moves_highlights(self.board,self.selected_square_idx)
        self.board_gui.draw_pieces(self.board,self.selected_square_idx,bool(self.dragging_piece_img))
        if self.dragging_piece_img and self.selected_square_idx is not None: self.screen.blit(self.dragging_piece_img,self.dragging_piece_img.get_rect(center=pygame.mouse.get_pos()))
        self._check_game_over_conditions(); self._update_status_message()
        if self.awaiting_promotion and self.is_player_turn_now(): self.promotion_choice_rects=self.board_gui.draw_promotion_choice(self.board.turn,pygame.mouse.get_pos())
        if self.ai_is_actively_thinking and not self.game_is_over:
            self._draw_ai_thinking_overlay(); draw_info_panel(self.screen,"AI is thinking...",INFO_FONT)
        else:
            if self.game_is_over: self._draw_game_over_screen()
            draw_info_panel(self.screen,self.status_message,INFO_FONT)
        self.draw_buttons(); pygame.display.flip()
    def run(self):
        clock=pygame.time.Clock(); running=True
        while running:
            if self.game_state=="GAME_OVER_DISPLAY" and pygame.time.get_ticks()-self.game_over_time>CONFIG['timing']['game_over_delay_ms']: self._reset_game_for_new_game_button()
            if self.hint_thread and not self.hint_thread.is_alive():
                try: self.hint_move=self.hint_queue.get_nowait(); self.hint_display_until=pygame.time.get_ticks()+2000
                except queue.Empty: pass
                self.hint_thread=None
            for event in pygame.event.get():
                if event.type==pygame.QUIT: running=False
                self.handle_input(event)
            if self.game_state=="PLAYING": self.update_ai() 
            self.draw(); clock.tick(CONFIG['timing']['fps'])
        if self.stop_search_event: self.stop_search_event.set()
        pygame.quit(); sys.exit()

def draw_info_panel(screen,message,font):
    C=CONFIG['colors']; panel_y=Y_POS_INFO_PANEL; pygame.draw.rect(screen,C['info_panel_bg'],pygame.Rect(CENTRAL_COLUMN_X_START,panel_y,CENTRAL_COLUMN_WIDTH,INFO_PANEL_HEIGHT))
    text_surf=font.render(message,True,C['white_text']); screen.blit(text_surf,text_surf.get_rect(center=(CENTRAL_COLUMN_X_START+CENTRAL_COLUMN_WIDTH//2,panel_y+INFO_PANEL_HEIGHT//2)))

if __name__ == "__main__":
    pygame.init()
    initialize_game()
    main_screen_surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Chess AI")
    load_assets()
    game = Game(main_screen_surface)
    game.run()