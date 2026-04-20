import chess
import chess.polyglot
import random
import threading
import queue
import time

# --- Piece-Square Tables ---
pawn_table = [0,0,0,0,0,0,0,0,50,50,50,50,50,50,50,50,10,10,20,30,30,20,10,10,5,5,10,25,25,10,5,5,0,0,0,20,20,0,0,0,5,-5,-10,0,0,-10,-5,5,5,10,10,-20,-20,10,10,5,0,0,0,0,0,0,0,0]
knight_table = [-50,-40,-30,-30,-30,-30,-40,-50,-40,-20,0,0,0,0,-20,-40,-30,0,10,15,15,10,0,-30,-30,5,15,20,20,15,5,-30,-30,0,15,20,20,15,0,-30,-30,5,10,15,15,10,5,-30,-40,-20,0,5,5,0,-20,-40,-50,-40,-30,-30,-30,-30,-40,-50]
bishop_table = [-20,-10,-10,-10,-10,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,10,10,5,0,-10,-10,5,5,10,10,5,5,-10,-10,0,10,10,10,10,0,-10,-10,10,10,10,10,10,10,-10,-10,5,0,0,0,0,5,-10,-20,-10,-10,-10,-10,-10,-10,-20]
rook_table = [0,0,0,0,0,0,0,0,5,10,10,10,10,10,10,5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,0,0,0,5,5,0,0,0]
queen_table = [-20,-10,-10,-5,-5,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,5,5,5,0,-10,-5,0,5,5,5,5,0,-5,0,0,5,5,5,5,0,-5,-10,5,5,5,5,5,0,-10,-10,0,5,0,0,0,0,-10,-20,-10,-10,-5,-5,-10,-10,-20]
king_mg_table = [-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-20,-30,-30,-40,-40,-30,-30,-20,-10,-20,-20,-20,-20,-20,-20,-10,20,20,0,0,0,0,20,20,20,30,10,0,0,10,30,20]
king_eg_table = [-50,-40,-30,-20,-20,-30,-40,-50,-30,-20,-10,0,0,-10,-20,-30,-30,-10,20,30,30,20,-10,-30,-30,-10,30,40,40,30,-10,-30,-30,-10,30,40,40,30,-10,-30,-30,-10,20,30,30,20,-10,-30,-30,-30,0,0,0,0,-30,-30,-50,-30,-30,-30,-30,-30,-30,-50]
piece_square_tables = { chess.PAWN: pawn_table, chess.KNIGHT: knight_table, chess.BISHOP: bishop_table, chess.ROOK: rook_table, chess.QUEEN: queen_table, chess.KING: king_mg_table }
piece_values = { chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000 }

passed_pawn_bonus = [0, 10, 30, 60, 100, 150, 200, 0]
ROOK_OPEN_FILE_BONUS = 20
ROOK_SEMI_OPEN_FILE_BONUS = 10
MOBILITY_BONUS_PER_MOVE = 2

EXACT_FLAG, LOWERBOUND_FLAG, UPPERBOUND_FLAG = 0, 1, 2
TIME_UP_FLAG = -9999999
INFINITY = 1000000
MATE_SCORE = 999999

def is_endgame(b):
    queens = len(b.pieces(chess.QUEEN, chess.WHITE)) + len(b.pieces(chess.QUEEN, chess.BLACK))
    minors = len(b.pieces(chess.KNIGHT, chess.WHITE)) + len(b.pieces(chess.KNIGHT, chess.BLACK)) + \
             len(b.pieces(chess.BISHOP, chess.WHITE)) + len(b.pieces(chess.BISHOP, chess.BLACK))
    return queens == 0 or (queens == 2 and minors <= 2)

def evaluate_board(b):
    if b.is_checkmate(): return -MATE_SCORE if b.turn == chess.WHITE else MATE_SCORE
    if b.is_stalemate() or b.is_insufficient_material() or b.is_seventyfive_moves() or b.is_fivefold_repetition() or b.is_repetition(3): return 0
    
    t_eval = 0
    ieg_flag = is_endgame(b)
    
    white_pawns = int(b.pieces(chess.PAWN, chess.WHITE))
    black_pawns = int(b.pieces(chess.PAWN, chess.BLACK))
    
    for pt in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]:
        table = king_eg_table if ieg_flag and pt == chess.KING else piece_square_tables.get(pt)
        
        for sq in b.pieces(pt, chess.WHITE):
            t_eval += piece_values[pt] + (table[sq] if table else 0)
            if pt == chess.PAWN:
                t_eval += passed_pawn_bonus[chess.square_rank(sq)]
            elif pt == chess.ROOK:
                file_mask = chess.BB_FILES[chess.square_file(sq)]
                if not (file_mask & white_pawns):
                    if not (file_mask & black_pawns): t_eval += ROOK_OPEN_FILE_BONUS
                    else: t_eval += ROOK_SEMI_OPEN_FILE_BONUS
                    
        for sq in b.pieces(pt, chess.BLACK):
            t_eval -= piece_values[pt] + (table[chess.square_mirror(sq)] if table else 0)
            if pt == chess.PAWN:
                t_eval -= passed_pawn_bonus[7 - chess.square_rank(sq)]
            elif pt == chess.ROOK:
                file_mask = chess.BB_FILES[chess.square_file(sq)]
                if not (file_mask & black_pawns):
                    if not (file_mask & white_pawns): t_eval -= ROOK_OPEN_FILE_BONUS
                    else: t_eval -= ROOK_SEMI_OPEN_FILE_BONUS
                    
    mobility = b.legal_moves.count()
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

def quiescence_search(board, alpha, beta, stop_event, depth=0, max_q_depth=10):
    if stop_event.is_set(): return TIME_UP_FLAG
    stand_pat = evaluate_board(board)
    
    if depth >= max_q_depth: return stand_pat
    
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
        score = quiescence_search(board, alpha, beta, stop_event, depth + 1, max_q_depth)
        board.pop()
        
        if score == TIME_UP_FLAG: return TIME_UP_FLAG
        if board.turn == chess.WHITE:
            alpha = max(alpha, score)
            if alpha >= beta: break
        else:
            beta = min(beta, score)
            if beta <= alpha: break
            
    return alpha if board.turn == chess.WHITE else beta

def minimax(board, depth, alpha, beta, maximizing_player, transposition_table, stop_event, stats, best_move_from_prev_iter=None, killer_moves=None):
    stats['nodes'] += 1
    if killer_moves is None: killer_moves = {}
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
            
    if depth <= 0 or board.is_game_over(claim_draw=True):
        return quiescence_search(board, alpha, beta, stop_event), None

    if depth >= 3 and not board.is_check() and not is_endgame(board):
        if not board.move_stack or board.peek() != chess.Move.null():
            board.push(chess.Move.null())
            if maximizing_player:
                null_eval, _ = minimax(board, depth - 1 - 2, alpha, beta, False, transposition_table, stop_event, stats, None, killer_moves)
                board.pop()
                if null_eval != TIME_UP_FLAG and null_eval >= beta: return beta, None
            else:
                null_eval, _ = minimax(board, depth - 1 - 2, alpha, beta, True, transposition_table, stop_event, stats, None, killer_moves)
                board.pop()
                if null_eval != TIME_UP_FLAG and null_eval <= alpha: return alpha, None
                
    def move_score(move):
        if move == best_move_from_prev_iter: return 10000000
        if board.is_capture(move): return 1000000 + get_move_score(board, move)
        if move in killer_moves.get(depth, []): return 900000
        return 0
        
    moves = sorted(list(board.legal_moves), key=move_score, reverse=True)
    best_move = None
    
    if maximizing_player:
        max_eval = -INFINITY
        for i, move in enumerate(moves):
            if stop_event.is_set(): return TIME_UP_FLAG, None
            board.push(move)
            if i == 0:
                eval, _ = minimax(board, depth - 1, alpha, beta, False, transposition_table, stop_event, stats, None, killer_moves)
            else:
                eval, _ = minimax(board, depth - 1, alpha, alpha + 1, False, transposition_table, stop_event, stats, None, killer_moves)
                if alpha < eval < beta:
                    eval, _ = minimax(board, depth - 1, eval, beta, False, transposition_table, stop_event, stats, None, killer_moves)
            board.pop()
            
            if eval == TIME_UP_FLAG: return TIME_UP_FLAG, None
            if eval > max_eval: max_eval = eval; best_move = move
            alpha = max(alpha, eval)
            if beta <= alpha:
                if not board.is_capture(move):
                    if depth not in killer_moves: killer_moves[depth] = []
                    if move not in killer_moves[depth]:
                        killer_moves[depth].insert(0, move)
                        if len(killer_moves[depth]) > 2: killer_moves[depth].pop()
                break
                
        entry = {'score': max_eval, 'depth': depth, 'move': best_move}
        if max_eval <= original_alpha: entry['flag'] = UPPERBOUND_FLAG
        elif max_eval >= beta: entry['flag'] = LOWERBOUND_FLAG
        else: entry['flag'] = EXACT_FLAG
        transposition_table[zobrist_key] = entry
        return max_eval, best_move
    else:
        min_eval = INFINITY
        for i, move in enumerate(moves):
            if stop_event.is_set(): return TIME_UP_FLAG, None
            board.push(move)
            if i == 0:
                eval, _ = minimax(board, depth - 1, alpha, beta, True, transposition_table, stop_event, stats, None, killer_moves)
            else:
                eval, _ = minimax(board, depth - 1, beta - 1, beta, True, transposition_table, stop_event, stats, None, killer_moves)
                if alpha < eval < beta:
                    eval, _ = minimax(board, depth - 1, alpha, eval, True, transposition_table, stop_event, stats, None, killer_moves)
            board.pop()
            
            if eval == TIME_UP_FLAG: return TIME_UP_FLAG, None
            if eval < min_eval: min_eval = eval; best_move = move
            beta = min(beta, eval)
            if beta <= alpha:
                if not board.is_capture(move):
                    if depth not in killer_moves: killer_moves[depth] = []
                    if move not in killer_moves[depth]:
                        killer_moves[depth].insert(0, move)
                        if len(killer_moves[depth]) > 2: killer_moves[depth].pop()
                break
                
        entry = {'score': min_eval, 'depth': depth, 'move': best_move}
        if min_eval <= original_alpha: entry['flag'] = UPPERBOUND_FLAG
        elif min_eval >= beta: entry['flag'] = LOWERBOUND_FLAG
        else: entry['flag'] = EXACT_FLAG
        transposition_table[zobrist_key] = entry
        return min_eval, best_move

def iterative_deepening_search(board, maximizing_player, transposition_table, stop_event, time_limit, start_time, thread_offset=0):
    if len(transposition_table) > 1000000: transposition_table.clear()
        
    best_move_so_far = None
    killer_moves = {}
    previous_score = 0
    stable_move_count = 0
    previous_best = None
    stats = {'nodes': 0}
    
    start_depth = 1 + thread_offset
    
    for depth in range(start_depth, 100):
        if stop_event.is_set(): break
        
        if depth > 3 and previous_score is not None:
            alpha = previous_score - 50
            beta = previous_score + 50
        else:
            alpha = -INFINITY
            beta = INFINITY
            
        score, move = minimax(board, depth, alpha, beta, maximizing_player, transposition_table, stop_event, stats, best_move_so_far, killer_moves)
        
        if score <= alpha or score >= beta:
            score, move = minimax(board, depth, -INFINITY, INFINITY, maximizing_player, transposition_table, stop_event, stats, best_move_so_far, killer_moves)
            
        if score == TIME_UP_FLAG: break
        
        previous_score = score
        if move: best_move_so_far = move
        
        elapsed = time.time() - start_time
        
        # --- THE PERFORMANCE LOGGER ---
        if thread_offset == 0:
            nps = int(stats['nodes'] / elapsed) if elapsed > 0 else 0
            print(f"Depth: {depth} | Score: {score} | Nodes: {stats['nodes']} | Time: {elapsed:.2f}s | NPS: {nps}")

        # --- EARLY EXIT LOGIC ---
        if abs(score) >= MATE_SCORE - 100:
            if thread_offset == 0: print(f"--> [MATE FOUND] Forced mate detected! Snapping move instantly.")
            break
            
        if move == previous_best:
            stable_move_count += 1
        else:
            stable_move_count = 0
            previous_best = move
            
        if stable_move_count >= 2 and depth >= 5:
            if thread_offset == 0: print(f"--> [STABLE MOVE] Best move {move} hasn't changed. Exiting early.")
            break

        # The "30% Soft Limit": If we used too much time, don't risk starting another depth.
        if elapsed > (time_limit * 0.3) and depth >= 4:
            if thread_offset == 0: print(f"--> [SOFT LIMIT] Time usage ({elapsed:.2f}s) exceeded 30% of {time_limit}s. Exiting early.")
            break
            
    if best_move_so_far is None and thread_offset == 0:
        legal_moves = list(board.legal_moves)
        if legal_moves: best_move_so_far = random.choice(legal_moves)
        
    return best_move_so_far

def get_ai_move_threaded_worker(board_fen, time_limit, maximizing_player, result_queue, transposition_table, stop_event):
    start_time = time.time()
    timer = threading.Timer(time_limit, stop_event.set)
    timer.start()
    
    num_threads = 4 
    threads = []
    
    def worker(thread_id):
        thread_board = chess.Board(board_fen)
        if thread_id == 0:
            best_move = iterative_deepening_search(thread_board, maximizing_player, transposition_table, stop_event, time_limit, start_time, thread_offset=0)
            result_queue.put(best_move)
            stop_event.set()
        else:
            iterative_deepening_search(thread_board, maximizing_player, transposition_table, stop_event, time_limit, start_time, thread_offset=thread_id)

    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        t.daemon = True
        t.start()
        threads.append(t)
        
    for t in threads: t.join()
        
    timer.cancel()
    if not stop_event.is_set(): stop_event.set()