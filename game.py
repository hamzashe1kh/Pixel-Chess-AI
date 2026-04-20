import pygame
import chess
import chess.polyglot
import threading
import queue
import random
import sys

from engine import *
import ui

class Game:
    def __init__(self, screen):
        self.screen=screen; self.game_state="SETTINGS"
        self.temp_human_is_white=True; self.temp_search_time=ui.CONFIG['ai']['difficulty']['medium']['time_seconds']
        self.human_is_white=True; self.search_time=self.temp_search_time
        self.board_gui=ui.BoardGUI(screen, self.human_is_white)
        self.button_pressed_state={}; self.ai_is_actively_thinking=False; self.stop_search_event=None
        self.ai_thread=None; self.ai_move_queue=queue.Queue()
        self.hint_thread=None; self.hint_queue=queue.Queue()
        self.player_mode="HUMAN_VS_AI"
        self.transposition_table={}
        self.show_history = True # Toggle state for history panel
        
        try:
            book_path=ui.get_resource_path(ui.CONFIG['assets']['opening_book_path'])
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
        self.ai_response_message=""; self.ai_response_message_until=0
        self.resignation_winner=None; self.game_over_time=0; self.current_eval_score=0.0
        self.pending_ai_move=None; self.ai_turn_start_time=0; self.aivsai_delay_until=0; self.transposition_table.clear()
        self._update_status_message()
        
    def _get_game_settings_gui(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1: return
        pos = event.pos
        if getattr(self, 'player_mode_btn_rect', pygame.Rect(0,0,0,0)).collidepoint(pos): self.player_mode="HUMAN_VS_HUMAN" if self.player_mode=="HUMAN_VS_AI" else "HUMAN_VS_AI"; ui.play_sound("button_click")
        elif self.player_mode=="HUMAN_VS_AI" and getattr(self, 'side_btn_rect', pygame.Rect(0,0,0,0)).collidepoint(pos): self.temp_human_is_white=not self.temp_human_is_white; ui.play_sound("button_click")
        elif self.player_mode=="HUMAN_VS_AI" and getattr(self, 'easy_button_rect', pygame.Rect(0,0,0,0)).collidepoint(pos): self.temp_search_time=ui.CONFIG['ai']['difficulty']['easy']['time_seconds']; ui.play_sound("button_click")
        elif self.player_mode=="HUMAN_VS_AI" and getattr(self, 'medium_button_rect', pygame.Rect(0,0,0,0)).collidepoint(pos): self.temp_search_time=ui.CONFIG['ai']['difficulty']['medium']['time_seconds']; ui.play_sound("button_click")
        elif self.player_mode=="HUMAN_VS_AI" and getattr(self, 'hard_button_rect', pygame.Rect(0,0,0,0)).collidepoint(pos): self.temp_search_time=ui.CONFIG['ai']['difficulty']['hard']['time_seconds']; ui.play_sound("button_click")
        elif getattr(self, 'start_button_rect', pygame.Rect(0,0,0,0)).collidepoint(pos):
            self.human_is_white=self.temp_human_is_white; self.search_time=self.temp_search_time
            perspective=self.human_is_white if self.player_mode=="HUMAN_VS_AI" else True
            if self.board_gui is None or self.board_gui.human_is_white_player!=perspective: self.board_gui=ui.BoardGUI(self.screen, perspective)
            self._reset_game_state_vars(); self.game_state="PLAYING"; ui.play_sound("button_click")
            
    def _draw_settings_screen(self):
        C=ui.CONFIG['colors']; self.screen.fill(C['settings_bg'])
        panel_w,panel_h=600,450; panel_rect=pygame.Rect((ui.SCREEN_WIDTH-panel_w)/2,(ui.SCREEN_HEIGHT-panel_h)/2,panel_w,panel_h)
        pygame.draw.rect(self.screen,C['settings_panel_bg'],panel_rect,border_radius=10); pygame.draw.rect(self.screen,C['settings_panel_border'],panel_rect,3,border_radius=10)
        title_surf=ui.GAME_OVER_FONT.render("Chess AI",True,C['settings_text']); self.screen.blit(title_surf,title_surf.get_rect(centerx=panel_rect.centerx,y=panel_rect.y+20))
        def draw_section(title,y): text_surf=ui.INFO_FONT.render(title,True,C['settings_text']); self.screen.blit(text_surf,text_surf.get_rect(left=panel_rect.left+30,y=panel_rect.y+y))
        btn_w,btn_h,btn_pad=180,45,10
        draw_section("Game Mode",90); mode_y=panel_rect.y+130
        self.player_mode_btn_rect=pygame.Rect(panel_rect.centerx-btn_w/2,mode_y,btn_w,btn_h)
        self.board_gui.draw_settings_button("Human vs AI" if self.player_mode=="HUMAN_VS_AI" else "Human vs Human",self.player_mode_btn_rect,True)
        
        if self.player_mode=="HUMAN_VS_AI":
            draw_section("Your Side",190); side_y=panel_rect.y+230
            self.side_btn_rect=pygame.Rect(panel_rect.centerx-btn_w/2,side_y,btn_w,btn_h)
            self.board_gui.draw_settings_button("White" if self.temp_human_is_white else "Black",self.side_btn_rect,True)
            
            draw_section("Difficulty", 290)
            diff_y = panel_rect.y + 330
            easy_t,med_t,hard_t=ui.CONFIG['ai']['difficulty']['easy']['time_seconds'],ui.CONFIG['ai']['difficulty']['medium']['time_seconds'],ui.CONFIG['ai']['difficulty']['hard']['time_seconds']
            self.easy_button_rect=pygame.Rect(panel_rect.centerx-btn_w*1.5-btn_pad,diff_y,btn_w,btn_h); self.board_gui.draw_settings_button(f"Easy ({easy_t}s)",self.easy_button_rect,self.temp_search_time==easy_t)
            self.medium_button_rect=pygame.Rect(panel_rect.centerx-btn_w/2,diff_y,btn_w,btn_h); self.board_gui.draw_settings_button(f"Medium ({med_t}s)",self.medium_button_rect,self.temp_search_time==med_t)
            self.hard_button_rect=pygame.Rect(panel_rect.centerx+btn_w/2+btn_pad,diff_y,btn_w,btn_h); self.board_gui.draw_settings_button(f"Hard ({hard_t}s)",self.hard_button_rect,self.temp_search_time==hard_t)
            
        self.start_button_rect=self.board_gui.draw_button("Start Game",panel_rect.centerx-100,panel_rect.bottom-70,200,50,ui.INFO_FONT)
        pygame.display.flip()
        
    def _reset_game_for_new_game_button(self): self.game_state="SETTINGS"
    
    def _undo_action_button(self): 
        if not self.awaiting_promotion and not self.ai_is_actively_thinking: self._undo_last_pair_of_moves()
        
    def _resign_action_button(self):
        if not self.game_is_over: self.game_is_over=True; ui.play_sound("game_end"); self.resignation_winner=chess.BLACK if self.board.turn == chess.WHITE else chess.WHITE; self.game_state="GAME_OVER_DISPLAY"; self.game_over_time=pygame.time.get_ticks()
        
    def _get_hint_action(self):
        if self.is_player_turn_now() and not self.game_is_over and not (self.hint_thread and self.hint_thread.is_alive()) and not self.ai_is_actively_thinking:
            self.stop_search_event=threading.Event()
            hint_time = min(self.search_time, 1.5)
            self.hint_thread=threading.Thread(target=get_ai_move_threaded_worker,args=(self.board.fen(),hint_time,self.board.turn==chess.WHITE,self.hint_queue,self.transposition_table,self.stop_search_event),daemon=True); self.hint_thread.start()
            
    def _update_status_message(self):
        if self.ai_is_actively_thinking and not(self.hint_thread and self.hint_thread.is_alive()): self.status_message=f"AI ({'White' if self.board.turn==chess.WHITE else 'Black'}) thinking"
        elif self.ai_response_message and pygame.time.get_ticks()<self.ai_response_message_until: self.status_message=self.ai_response_message
        elif self.awaiting_promotion and self.is_player_turn_now(): self.status_message="Choose promotion piece!"
        elif self.game_is_over:
            if self.resignation_winner is not None: self.status_message=f"{'Black' if self.resignation_winner==chess.BLACK else 'White'} wins by Resignation."
            else:
                outcome=self.board.outcome()
                if outcome: self.status_message=f"Checkmate! {'Black' if outcome.winner==chess.BLACK else 'White'} Wins!" if outcome.termination==chess.Termination.CHECKMATE else f"Draw: {outcome.termination.name.replace('_',' ').title()}."
                else: self.status_message="Game Over"
        else: 
            tc="White" if self.board.turn==chess.WHITE else "Black"; cs=" (Check!)" if self.board.is_check() else ""
            if self.player_mode=="HUMAN_VS_HUMAN": self.status_message=f"{tc}'s turn{cs}"
            elif self.is_player_turn_now(): self.status_message=f"Your ({tc}) turn{cs}"
            else: self.status_message=f"AI ({tc}) to move..."
        if not self.game_is_over and not self.ai_is_actively_thinking: self.status_message+=f" | Eval: {self.current_eval_score/100:+.2f}"
        
    def is_player_turn_now(self):
        if self.player_mode == "HUMAN_VS_HUMAN": return True
        return self.player_mode=="HUMAN_VS_AI" and ((self.human_is_white and self.board.turn==chess.WHITE) or (not self.human_is_white and self.board.turn==chess.BLACK))
    
    def _handle_move_push_and_history(self,move):
        san=self.board.san(move); captured=self.board.piece_at(move.to_square)
        if self.board.is_en_passant(move): captured=chess.Piece(chess.PAWN,not self.board.turn)
        self.board_move_stack_for_undo.append(self.board.fen()); self.board.push(move); self.move_history_san.append(san); self.last_played_move=move
        if captured: (self.captured_by_white if self.board.turn==chess.BLACK else self.captured_by_black).append(captured.symbol())
        ui.play_sound("capture" if captured else "move"); 
        if self.board.is_check(): ui.play_sound("check")
        self.current_eval_score=evaluate_board(self.board)
        
        if self.player_mode == "HUMAN_VS_HUMAN":
            self.board_gui.human_is_white_player = not self.board_gui.human_is_white_player
        
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
        self.resignation_winner=None; self.current_eval_score=evaluate_board(self.board); self._update_status_message(); ui.play_sound("move") 
        
        if self.player_mode == "HUMAN_VS_HUMAN":
            self.board_gui.human_is_white_player = not self.board_gui.human_is_white_player
            
    def handle_input(self,event):
        if self.game_state=="SETTINGS": self._get_game_settings_gui(event); return
        if self.ai_is_actively_thinking and event.type!=pygame.QUIT:
            if event.type==pygame.MOUSEBUTTONUP and getattr(self, 'resign_button_rect', pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                ui.play_sound("button_click"); self.stop_search_event.set(); self._resign_action_button()
            return
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            pos=event.pos; buttons={"undo":self.undo_button_rect,"resign":self.resign_button_rect,"hint":self.hint_button_rect,"history":self.hist_button_rect}
            for name,rect in buttons.items():
                if rect and rect.collidepoint(pos):
                    is_interactive=not self.ai_is_actively_thinking and not self.game_is_over and not (self.hint_thread and self.hint_thread.is_alive())
                    is_enabled=False
                    # GHOST CLICK FIX: The internal button pressed state now strictly checks if it is enabled
                    if name=="undo": is_enabled=is_interactive and len(self.board.move_stack)>0
                    elif name=="resign": is_enabled=is_interactive
                    elif name=="hint": is_enabled=is_interactive and self.is_player_turn_now()
                    elif name=="history": is_enabled=True # History button is always enabled
                    
                    if is_enabled: 
                        self.button_pressed_state[name]=True
                    return
        if event.type==pygame.MOUSEBUTTONUP and event.button==1:
            pos=event.pos
            actions={"undo":self._undo_action_button,"resign":self._resign_action_button,"hint":self._get_hint_action}
            action_taken=False
            
            # Special check for history toggle
            rect=getattr(self, "hist_button_rect", None)
            if rect and rect.collidepoint(pos) and self.button_pressed_state.get("history"):
                ui.play_sound("button_click"); self.show_history = not self.show_history; action_taken=True
                
            for name,action in actions.items():
                rect=getattr(self,f"{name}_button_rect",None)
                if rect and rect.collidepoint(pos) and self.button_pressed_state.get(name):
                    ui.play_sound("button_click"); action(); action_taken=True
                    
            self.button_pressed_state.clear()
            if action_taken: return
            
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_n: ui.play_sound("button_click"); self._reset_game_for_new_game_button()
            elif event.key==pygame.K_u: ui.play_sound("button_click"); self._undo_action_button()
            return
        if self.awaiting_promotion and self.is_player_turn_now():
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                for rect,p_type in self.promotion_choice_rects:
                    if rect.collidepoint(event.pos):
                        ui.play_sound("button_click"); move=chess.Move(self.promotion_move_from,self.promotion_move_to,promotion=p_type)
                        if move in self.board.legal_moves: self._handle_move_push_and_history(move)
                        self.awaiting_promotion=False; self.selected_square_idx=None; self.dragging_piece_img=None; break
        elif not self.game_is_over and self.is_player_turn_now():
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                sq=self.board_gui.get_square_from_mouse(event.pos)
                if sq is not None:
                    piece=self.board.piece_at(sq)
                    if self.selected_square_idx is None and piece and piece.color==self.board.turn:
                        self.selected_square_idx=sq; self.dragging_piece_img=ui.LIFTED_PIECE_IMAGES.get(piece.symbol()); self.dragging_piece_original_square=sq
            elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
                if self.selected_square_idx is not None and self.dragging_piece_img:
                    dropped_sq=self.board_gui.get_square_from_mouse(event.pos)
                    if dropped_sq is not None and dropped_sq!=self.dragging_piece_original_square:
                        is_promo=any(chess.Move(self.selected_square_idx,dropped_sq,promotion=p) in self.board.legal_moves for p in ui.PROMOTION_TYPES)
                        if is_promo: self.awaiting_promotion=True; self.promotion_move_from=self.selected_square_idx; self.promotion_move_to=dropped_sq
                        else:
                            move=chess.Move(self.selected_square_idx,dropped_sq)
                            if move in self.board.legal_moves: self._handle_move_push_and_history(move)
                            else: ui.play_sound("illegal")
                    self.selected_square_idx=None; self.dragging_piece_img=None
                    
    def update_ai(self):
        if self.player_mode == "HUMAN_VS_HUMAN": return
        
        if self.pending_ai_move:
            if pygame.time.get_ticks()-self.ai_turn_start_time>ui.CONFIG['timing']['min_ai_turn_duration_ms']:
                self._handle_move_push_and_history(self.pending_ai_move)
                self.pending_ai_move=None; self.ai_is_actively_thinking=False; pygame.display.set_caption("Chess AI"); self._check_game_over_conditions(); self._update_status_message()
            return
            
        if not self.game_is_over and not self.is_player_turn_now() and not self.awaiting_promotion:
            if self.opening_book and len(self.board.move_stack)<ui.CONFIG['ai']['opening_book_max_moves']:
                try:
                    entry = self.opening_book.weighted_choice(self.board)
                    if entry: print("AI played from external book."); self.ai_is_actively_thinking=True; self.ai_turn_start_time=pygame.time.get_ticks(); self.pending_ai_move=entry.move; return
                except IndexError: pass 
                
            if not self.ai_is_actively_thinking:
                self.ai_is_actively_thinking=True; self.ai_turn_start_time=pygame.time.get_ticks(); self._update_status_message(); pygame.display.set_caption("Chess AI - AI Thinking...")
                self.stop_search_event=threading.Event()
                self.ai_thread=threading.Thread(target=get_ai_move_threaded_worker,args=(self.board.fen(),self.search_time,self.board.turn==chess.WHITE,self.ai_move_queue,self.transposition_table,self.stop_search_event),daemon=True); self.ai_thread.start()
            try:
                self.pending_ai_move=self.ai_move_queue.get_nowait()
                if not self.pending_ai_move and list(self.board.legal_moves): self.pending_ai_move=random.choice(list(self.board.legal_moves))
                self.ai_thread=None
            except queue.Empty: pass
            
    def _check_game_over_conditions(self):
        if not self.game_is_over and self.board.is_game_over(claim_draw=True): self.game_is_over=True; ui.play_sound("game_end"); self.game_state="GAME_OVER_DISPLAY"; self.game_over_time=pygame.time.get_ticks()
        
    def _draw_ai_thinking_overlay(self):
        C=ui.CONFIG['colors']; overlay=pygame.Surface((ui.BOARD_DRAW_WIDTH,ui.BOARD_DRAW_HEIGHT),pygame.SRCALPHA); overlay.fill(C['game_over_overlay']); self.screen.blit(overlay,(ui.BOARD_OFFSET_X,ui.BOARD_OFFSET_Y)) 
        message=f"AI ({'White' if self.board.turn==chess.WHITE else 'Black'}) thinking..."; text_surf=ui.OVERLAY_FONT.render(message,True,C['game_over_text'])
        if ui.SPINNER_FRAMES:
            spinner=ui.SPINNER_FRAMES[pygame.time.get_ticks()//ui.CONFIG['spinner']['animation_speed_ms']%len(ui.SPINNER_FRAMES)]
            total_w=text_surf.get_width()+15+spinner.get_width(); start_x=ui.BOARD_OFFSET_X+(ui.BOARD_DRAW_WIDTH-total_w)/2
            text_y=ui.BOARD_OFFSET_Y+(ui.BOARD_DRAW_HEIGHT-text_surf.get_height())/2
            self.screen.blit(text_surf,(start_x,text_y)); self.screen.blit(spinner,(start_x+text_surf.get_width()+15,text_y+(text_surf.get_height()-spinner.get_height())/2))
        else: ui.draw_text_wrapped(self.screen,message,ui.OVERLAY_FONT,C['game_over_text'],pygame.Rect(ui.BOARD_OFFSET_X+20,ui.BOARD_OFFSET_Y,ui.BOARD_DRAW_WIDTH-40,ui.BOARD_DRAW_HEIGHT),aa=True)
        
    def draw_buttons(self):
        y=ui.Y_POS_BUTTON_AREA+(ui.BUTTON_AREA_HEIGHT-ui.BUTTON_HEIGHT)//2; 
        total_w=(ui.ACTION_BUTTON_WIDTH*4)+(ui.BUTTON_PADDING*3)
        x=ui.CENTRAL_COLUMN_X_START+(ui.CENTRAL_COLUMN_WIDTH-total_w)//2; is_interactive=not self.ai_is_actively_thinking and not self.game_is_over
        
        self.undo_button_rect=self.board_gui.draw_button("Undo",x,y,ui.ACTION_BUTTON_WIDTH,ui.BUTTON_HEIGHT,ui.BUTTON_FONT,pressed=self.button_pressed_state.get("undo"),enabled=is_interactive and len(self.board.move_stack)>0); x+=ui.ACTION_BUTTON_WIDTH+ui.BUTTON_PADDING
        self.resign_button_rect=self.board_gui.draw_button("Resign",x,y,ui.ACTION_BUTTON_WIDTH,ui.BUTTON_HEIGHT,ui.BUTTON_FONT,pressed=self.button_pressed_state.get("resign"),enabled=(is_interactive or self.ai_is_actively_thinking)); x+=ui.ACTION_BUTTON_WIDTH+ui.BUTTON_PADDING
        self.hint_button_rect=self.board_gui.draw_button("Hint",x,y,ui.ACTION_BUTTON_WIDTH,ui.BUTTON_HEIGHT,ui.BUTTON_FONT,pressed=self.button_pressed_state.get("hint"),enabled=is_interactive and self.is_player_turn_now()); x+=ui.ACTION_BUTTON_WIDTH+ui.BUTTON_PADDING
        self.hist_button_rect=self.board_gui.draw_button("History",x,y,ui.ACTION_BUTTON_WIDTH,ui.BUTTON_HEIGHT,ui.BUTTON_FONT,pressed=self.button_pressed_state.get("history"),enabled=True)
        
    def _draw_game_over_screen(self):
        C=ui.CONFIG['colors']; overlay=pygame.Surface((ui.BOARD_DRAW_WIDTH,ui.BOARD_DRAW_HEIGHT),pygame.SRCALPHA); overlay.fill(C['game_over_overlay']); self.screen.blit(overlay,(ui.BOARD_OFFSET_X,ui.BOARD_OFFSET_Y)) 
        ui.draw_text_wrapped(self.screen,self.status_message,ui.GAME_OVER_FONT,C['game_over_text'],pygame.Rect(ui.BOARD_OFFSET_X+20,ui.BOARD_OFFSET_Y,ui.BOARD_DRAW_WIDTH-40,ui.BOARD_DRAW_HEIGHT),aa=True)
        
    def _draw_hint_highlight(self):
        if self.hint_move and pygame.time.get_ticks()<self.hint_display_until:
            for sq in [self.hint_move.from_square,self.hint_move.to_square]:
                x,y=self.board_gui.get_pygame_coords(sq); hs=pygame.Surface((ui.SQUARE_SIZE,ui.SQUARE_SIZE),pygame.SRCALPHA); hs.fill(ui.CONFIG['colors']['hint']); self.screen.blit(hs,(x,y))
        else: self.hint_move=None
        
    def _draw_evaluation_bar(self):
        C=ui.CONFIG['colors']; max_eval=800; bar_rect=pygame.Rect(ui.X_POS_EVAL_BAR,ui.EVAL_BAR_Y,ui.EVAL_BAR_WIDTH,ui.BOARD_DRAW_HEIGHT)
        clamped_score=max(-max_eval,min(max_eval,self.current_eval_score)); white_prop=(clamped_score+max_eval)/(2*max_eval); white_h=bar_rect.height*white_prop
        
        # UI FIX: The "White Block" is now a clear evaluation bar with a dark background and a marker.
        pygame.draw.rect(self.screen, (40, 40, 40), bar_rect)
        white_rect=pygame.Rect(int(bar_rect.x),int(bar_rect.y+(bar_rect.height-white_h)),int(bar_rect.width),int(white_h))
        pygame.draw.rect(self.screen, (240, 240, 240), white_rect)
        
        center_y = bar_rect.y + bar_rect.height // 2
        pygame.draw.line(self.screen, (150, 50, 50), (bar_rect.x, center_y), (bar_rect.x + bar_rect.width, center_y), 2)
        pygame.draw.rect(self.screen,C['button_border'],bar_rect,2)
        
    def draw(self):
        if self.game_state=="SETTINGS": self._draw_settings_screen(); return
        self.screen.fill(ui.CONFIG['colors']['screen_bg'])
        self.board_gui.draw_board_squares(); self.board_gui.draw_coordinates(); self._draw_evaluation_bar()
        self.board_gui.draw_move_history(self.move_history_san, ui.MOVE_HISTORY_FONT, show=self.show_history)
        
        if self.board_gui.human_is_white_player: 
            self.board_gui.draw_captured_pieces(self.captured_by_black,True)
            self.board_gui.draw_captured_pieces(self.captured_by_white,False)
        else: 
            self.board_gui.draw_captured_pieces(self.captured_by_white,True)
            self.board_gui.draw_captured_pieces(self.captured_by_black,False)
            
        if not self.game_is_over:
            y=ui.Y_POS_BOTTOM_CAPTURED_AREA if self.is_player_turn_now() else ui.Y_POS_TOP_CAPTURED_AREA
            pygame.draw.rect(self.screen,ui.CONFIG['colors']['turn_indicator_highlight'],(ui.BOARD_OFFSET_X,y,ui.BOARD_DRAW_WIDTH,int(ui.CAPTURED_AREA_HEIGHT)),3)
        self._draw_hint_highlight(); self.board_gui.draw_last_move_highlight(self.last_played_move); self.board_gui.draw_check_highlight(self.board)
        if self.is_player_turn_now() and not self.game_is_over and not self.awaiting_promotion and self.selected_square_idx is not None:
            self.board_gui.draw_selected_and_legal_moves_highlights(self.board,self.selected_square_idx)
        self.board_gui.draw_pieces(self.board,self.selected_square_idx,bool(self.dragging_piece_img))
        if self.dragging_piece_img and self.selected_square_idx is not None: self.screen.blit(self.dragging_piece_img,self.dragging_piece_img.get_rect(center=pygame.mouse.get_pos()))
        self._check_game_over_conditions(); self._update_status_message()
        if self.awaiting_promotion and self.is_player_turn_now(): self.promotion_choice_rects=self.board_gui.draw_promotion_choice(self.board.turn,pygame.mouse.get_pos())
        if self.ai_is_actively_thinking and not self.game_is_over:
            self._draw_ai_thinking_overlay(); ui.draw_info_panel(self.screen,"AI is thinking...",ui.INFO_FONT)
        else:
            if self.game_is_over: self._draw_game_over_screen()
            ui.draw_info_panel(self.screen,self.status_message,ui.INFO_FONT)
        self.draw_buttons(); pygame.display.flip()
        
    def run(self):
        clock=pygame.time.Clock(); running=True
        while running:
            if self.game_state=="GAME_OVER_DISPLAY" and pygame.time.get_ticks()-self.game_over_time>ui.CONFIG['timing']['game_over_delay_ms']: self._reset_game_for_new_game_button()
            if self.hint_thread and not self.hint_thread.is_alive():
                try: self.hint_move=self.hint_queue.get_nowait(); self.hint_display_until=pygame.time.get_ticks()+2000
                except queue.Empty: pass
                self.hint_thread=None
            for event in pygame.event.get():
                if event.type==pygame.QUIT: running=False
                self.handle_input(event)
            if self.game_state=="PLAYING": self.update_ai() 
            self.draw(); clock.tick(ui.CONFIG['timing']['fps'])
        if self.stop_search_event: self.stop_search_event.set()
        pygame.quit(); sys.exit()