import pygame
import chess
import json
import sys
import os

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

# EXE Path Helper Function
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
        with open(get_resource_path(config_filename), 'r') as f: CONFIG = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e: 
        print(f"FATAL: Error with '{config_filename}': {e}. Cannot start."); sys.exit(1)
        
    layout = CONFIG['layout']; eval_bar = CONFIG.get('evaluation_bar', {'width': 20, 'padding_x': 10}); fonts = CONFIG['fonts']
    SQUARE_SIZE = layout['square_size']; COORDINATE_AREA_SIZE = layout['coordinate_area_size']; CAPTURED_AREA_HEIGHT = SQUARE_SIZE * layout['captured_area_height_scale']; CAPTURED_PIECE_DISPLAY_SIZE = int(SQUARE_SIZE * 0.55)
    
    # UI FIX: slightly wider history width to prevent cutoff
    MOVE_HISTORY_WIDTH = layout.get('move_history_width', 220) + 20 
    
    INFO_PANEL_HEIGHT = layout['info_panel_height']; BUTTON_AREA_HEIGHT = layout['button_area_height']; BUTTON_PADDING = layout['button_padding']
    NEW_GAME_BUTTON_WIDTH = layout['new_game_button_width']; ACTION_BUTTON_WIDTH = layout['action_button_width']; BUTTON_HEIGHT = layout['button_height']
    PROMOTION_CHOICE_IMG_SIZE = int(SQUARE_SIZE * layout['promotion_choice_scale']); PROMOTION_CHOICE_HEIGHT = PROMOTION_CHOICE_IMG_SIZE + 30
    LIFTED_PIECE_SCALE = layout['lifted_piece_scale']; LIFTED_PIECE_SIZE = int(SQUARE_SIZE * LIFTED_PIECE_SCALE)
    
    MOVE_HISTORY_LINE_HEIGHT = fonts.get('move_history_line_height', 20)
    MOVE_HISTORY_FONT_SIZE = fonts.get('move_history_font_size', 16)
    BUTTON_FONT_SIZE = fonts['button_font_size']
    
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
    
    font_path = get_resource_path(os.path.join(cfg_font['custom_font_path'], cfg_font['custom_font_filename'])) if cfg_font.get('custom_font_filename') else None
    
    try:
        INFO_FONT=pygame.font.Font(font_path, cfg_font['info_font_size'])
        MOVE_HISTORY_FONT=pygame.font.Font(font_path, MOVE_HISTORY_FONT_SIZE)
        BUTTON_FONT=pygame.font.Font(font_path, cfg_font['button_font_size'])
        COORD_FONT=pygame.font.Font(font_path, int(COORDINATE_AREA_SIZE * cfg_font['coord_font_size_scale'])); GAME_OVER_FONT=pygame.font.Font(font_path, cfg_font['game_over_font_size']); OVERLAY_FONT=pygame.font.Font(font_path, cfg_font['info_font_size']) 
    except pygame.error: 
        INFO_FONT=pygame.font.Font(None, cfg_font['info_font_size']); MOVE_HISTORY_FONT=pygame.font.Font(None, MOVE_HISTORY_FONT_SIZE); BUTTON_FONT=pygame.font.Font(None, cfg_font['button_font_size']); COORD_FONT=pygame.font.Font(None, int(COORDINATE_AREA_SIZE*cfg_font['coord_font_size_scale'])); GAME_OVER_FONT=pygame.font.Font(None, cfg_font['game_over_font_size']); OVERLAY_FONT=pygame.font.Font(None, cfg_font['info_font_size'])
        
    s_map={'P':'wP','N':'wKN','B':'wB','R':'wR','Q':'wQ','K':'wKI','p':'bP','n':'bKN','b':'bB','r':'bR','q':'bQ','k':'bKI'}
    for ps, fb in s_map.items():
        try: 
            fn = get_resource_path(os.path.join(cfg_assets['image_path'], f"{fb}.png"))
            oi=pygame.image.load(fn).convert_alpha()
            # Standard scaling keeps pixel art sharp
            PIECE_IMAGES[ps]=pygame.transform.scale(oi,(SQUARE_SIZE,SQUARE_SIZE)); LIFTED_PIECE_IMAGES[ps]=pygame.transform.scale(oi,(LIFTED_PIECE_SIZE, LIFTED_PIECE_SIZE)); CAPTURED_DISPLAY_PIECE_IMAGES[ps]=pygame.transform.scale(oi,(CAPTURED_PIECE_DISPLAY_SIZE, CAPTURED_PIECE_DISPLAY_SIZE))
            if ps.upper() in ['Q','R','B','N']: PROMOTION_PIECE_IMAGES[ps] = pygame.transform.scale(oi,(PROMOTION_CHOICE_IMG_SIZE, PROMOTION_CHOICE_IMG_SIZE))
        except pygame.error: pass
        
    if not pygame.mixer.get_init(): pygame.mixer.init()
    sound_files={"move":"move.wav","capture":"capture.wav","check":"check.wav","game_end":"game_end.wav", "button_click":"button.wav", "illegal":cfg_assets.get('illegal_move_sound',"illegal.wav")}
    for name, file in sound_files.items():
        try: SOUNDS[name] = pygame.mixer.Sound(get_resource_path(os.path.join(cfg_assets['sound_path'], file)))
        except (pygame.error, FileNotFoundError): SOUNDS[name] = None
        
    if cfg_assets.get('spinner_spritesheet_filename'):
        try:
            sheet=pygame.image.load(get_resource_path(os.path.join(cfg_assets['image_path'],cfg_assets['spinner_spritesheet_filename']))).convert_alpha()
            w,h,n=cfg_spinner['frame_width'],cfg_spinner['frame_height'],cfg_spinner['number_of_frames']
            size=(int(w*cfg_spinner['display_scale']),int(h*cfg_spinner['display_scale']))
            for i in range(n): 
                rect=pygame.Rect(i*w,0,w,h); surf=pygame.Surface(rect.size,pygame.SRCALPHA); surf.blit(sheet,(0,0),rect); SPINNER_FRAMES.append(pygame.transform.scale(surf,size))
        except Exception: pass

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

def draw_info_panel(screen,message,font):
    C=CONFIG['colors']; panel_y=Y_POS_INFO_PANEL; pygame.draw.rect(screen,C['info_panel_bg'],pygame.Rect(CENTRAL_COLUMN_X_START,panel_y,CENTRAL_COLUMN_WIDTH,INFO_PANEL_HEIGHT))
    text_surf=font.render(message,True,C['white_text']); screen.blit(text_surf,text_surf.get_rect(center=(CENTRAL_COLUMN_X_START+CENTRAL_COLUMN_WIDTH//2,panel_y+INFO_PANEL_HEIGHT//2)))

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
    def draw_move_history(self,hist,font,show=True):
        if not show: return # Toggle fix
        C=CONFIG['colors']; hx=X_POS_MOVE_HISTORY; hy=BOARD_OFFSET_Y; hh=BOARD_DRAW_HEIGHT
        pygame.draw.rect(self.screen,C['move_history_bg'],(hx,hy,MOVE_HISTORY_WIDTH,hh)); pygame.draw.rect(self.screen,C['promotion_border'],(hx,hy,MOVE_HISTORY_WIDTH,hh),2)
        
        yo=hy+10; max_moves=(hh-20)//MOVE_HISTORY_LINE_HEIGHT; start_idx=max(0,len(hist)-max_moves*2)
        if start_idx%2!=0: start_idx-=1
        move_num=(start_idx//2)+1
        for i in range(start_idx,len(hist),2):
            if yo>hy+hh-MOVE_HISTORY_LINE_HEIGHT-5: break 
            w=hist[i] if i<len(hist) else ""; b=hist[i+1] if i+1<len(hist) else ""
            line=f"{move_num}. {w:<7} {b:<7}"
            # UI FIX: Added extra padding (hx+15) so it doesn't get cut off on the left.
            surf=font.render(line,True,C['white_text']); self.screen.blit(surf,(hx+15,yo)); yo+=MOVE_HISTORY_LINE_HEIGHT; move_num+=1
            
    def draw_button(self,txt,x,y,w,h,font,pressed=False,enabled=True):
        C=CONFIG['colors']; rect=pygame.Rect(x,y,w,h)
        
        # GHOST CLICKING FIX: Hover logic now fully respects the "enabled" state
        if enabled:
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            bg = C['button_pressed_bg'] if pressed else (C['button_hover_bg'] if hovered else C['button_bg'])
            txt_color = C['button_text']
        else:
            bg = (50, 50, 50)
            txt_color = (120, 120, 120)
            
        pygame.draw.rect(self.screen,bg,rect); pygame.draw.rect(self.screen,C['button_border'],rect,2)
        offset=2 if pressed and enabled else 0
        surf=font.render(txt,True,txt_color); self.screen.blit(surf,surf.get_rect(center=(rect.centerx,rect.centery+offset)))
        return rect
        
    def draw_settings_button(self,text,rect,is_selected):
        C=CONFIG['colors']; hovered=rect.collidepoint(pygame.mouse.get_pos())
        bg=C['settings_button_selected_bg'] if is_selected else (C['settings_button_hover'] if hovered else C['settings_button'])
        pygame.draw.rect(self.screen,bg,rect,border_radius=5)
        text_surf=BUTTON_FONT.render(text,True,C['settings_text']); self.screen.blit(text_surf,text_surf.get_rect(center=rect.center))  