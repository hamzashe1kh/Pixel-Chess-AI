# ♟️ Retro-Pixel Chess AI

A high-performance, fully playable Chess Engine and graphical interface built entirely in Python. This project combines a nostalgic pixel-art aesthetic with a deeply optimized, multi-threaded AI backend. 

---

## 🚀 Tech Stack

* **Language:** Python 3.x
* **Graphics & Audio:** `pygame` (Hardware-accelerated 2D rendering, event handling, and audio mixing)
* **Board Representation:** `python-chess` (Strict rule enforcement, bitboard state handling, and FEN/SAN parsing)
* **Packaging:** `pyinstaller` (Compiled into a standalone `.exe` for deployment)

---

## ⚙️ Architecture: How the Parts Work Together

The project is divided into strict modular components to separate the graphical interface from the heavy mathematical processing of the AI.

1. **The Entry Point (`main.py`):** Bootstraps the application, loads the configuration/assets, and launches the Pygame window.  
2. **The Front-End (`ui.py` & `game.py`):**  
   * `ui.py` handles all the pixel math—drawing the board, high-DPI sprite scaling, and rendering the dynamic layout (evaluation bar, history log).  
   * `game.py` acts as the **State Controller**. It listens for mouse clicks, validates legal moves using `python-chess`, updates the visual board, and determines when it is the AI's turn to play.  
3. **The Communication Bridge (Threading):** When the AI needs to think, `game.py` does not freeze the screen. Instead, it packages the current board state (as a FEN string) and passes it to `engine.py` on a separate background thread.  
4. **The Back-End (`engine.py`):** The core AI receives the board state, searches millions of possible future moves using optimized algorithms, and returns the absolute best move back to the UI thread to be played.  

---

## 🧠 The Engine: Algorithms & Minimax Deep Dive

The AI does not rely on pre-programmed responses (except for the initial opening book). It calculates the best move dynamically using a highly optimized variant of the **Minimax Algorithm**.

### 1. The Core: Minimax Search

At its heart, the engine uses Minimax to look ahead into the future.

* **Maximizing (The AI):** The engine evaluates the board and tries to find a sequence of moves that yields the highest possible score (+ points for capturing pieces, controlling the center, etc.).  
* **Minimizing (The Human):** The engine assumes that *you* will play perfectly. It calculates your future moves based on what will cause the most damage to its own score.  

By recursively simulating these back-and-forth turns down to a specific depth, the AI identifies the move that guarantees the best worst-case scenario.

---

### 2. Alpha-Beta Pruning & PVS

Standard Minimax is too slow for chess because the game tree grows exponentially. To address this, the engine uses **Principal Variation Search (PVS)**, an advanced form of Alpha-Beta pruning.

* If the engine finds a move that is worse than a previously evaluated move, it prunes that branch entirely.  
* This allows the engine to skip evaluating millions of unnecessary positions while maintaining accuracy.  

---

### 3. Bitboard Evaluation

Instead of iterating through a 64-square array, the engine uses **Bitboards**, representing the board as 64-bit integers.

This enables extremely fast computation using bitwise operations such as `&`, `|`, and `^`, allowing near-instant evaluation of positions and attacks.

---

### 4. Lazy SMP (Symmetric Multiprocessing)

The engine uses a multi-threaded architecture to improve performance:

* The main thread evaluates the primary move sequence.  
* Additional threads simultaneously evaluate alternative depths and variations.  

**Transposition Tables (Zobrist Hashing):**  
All threads share a memory cache. If a board state has already been evaluated, it is reused instead of recalculated, significantly improving performance.

---

### 5. Quiescence Search & Aspiration Windows

* **Quiescence Search:** Prevents the horizon effect by continuing evaluation during volatile capture sequences until a stable position is reached.  
* **Aspiration Windows:** Uses previous evaluations to narrow score ranges, enabling faster pruning and search efficiency.  

---

## 🎨 Graphical User Interface (GUI)

* **Retro Aesthetic:** Nearest-neighbor scaling keeps pixel-art sprites sharp and visually consistent.  
* **Custom Sound Design:** Audio feedback for moves, captures, checks, and game-over states.  
* **Dynamic Information Panels:**  
  * Real-time evaluation bar  
  * Move history (Standard Algebraic Notation)  
  * Highlighting for valid moves, selected pieces, and active checks  

---

## 📦 Installation & Usage

### Option 1: Standalone Executable

Download the compiled `.exe` from the **Releases** section and run it directly. No setup required.

---

### Option 2: Run from Source

**1. Clone the repository:**
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
cd YOUR_REPOSITORY_NAME
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```

**3. Run the project:**
```bash
python main.py
```

