import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class GameAI:
    def __init__(self, driver):
        self.driver = driver
        self.prev_score = 0
        self.max_depth = 3  # Search depth for expectimax
        
    def get_game_state(self):
        """Retrieve game state from local storage"""
        state_json = self.driver.execute_script(
            "return localStorage.getItem('2048GameState_hardcore');"
        )
        return json.loads(state_json)
    
    def make_move(self, direction):
        """Send move to the game"""
        body = self.driver.find_element(By.TAG_NAME, 'body')
        body.send_keys(direction)
        time.sleep(0.1)  # Allow animation to complete
        
    def get_grid(self):
        """Get current 4x4 grid from game state"""
        state = self.get_game_state()
        grid_1d = state['grid']
        return [grid_1d[i:i+4] for i in range(0, 16, 4)]
    
    def get_score(self):
        """Get current score from game state"""
        return self.get_game_state()['score']
    
    def get_possible_moves(self, grid):
        """Get all valid moves for current grid"""
        moves = []
        for direction in [Keys.LEFT, Keys.RIGHT, Keys.UP, Keys.DOWN]:
            if self.simulate_move(grid, direction) != grid:
                moves.append(direction)
        return moves
    
    def simulate_move(self, grid, direction):
        """Simulate a move without modifying actual game state"""
        # Create a deep copy of the grid
        rows = [row[:] for row in grid]
        
        if direction in (Keys.LEFT, Keys.RIGHT):
            for i in range(4):
                # Extract non-zero tiles
                non_zero = [x for x in rows[i] if x != 0]
                if not non_zero:
                    continue
                    
                # For RIGHT: process tiles from right to left
                if direction == Keys.RIGHT:
                    non_zero.reverse()
                    
                # Merge adjacent tiles
                j = 0
                while j < len(non_zero) - 1:
                    if non_zero[j] == non_zero[j+1]:
                        non_zero[j] *= 2
                        non_zero.pop(j+1)
                    j += 1
                    
                # Reverse back if needed
                if direction == Keys.RIGHT:
                    non_zero.reverse()
                    
                # Pad with zeros in correct positions
                if direction == Keys.LEFT:
                    rows[i] = non_zero + [0] * (4 - len(non_zero))
                else:  # RIGHT
                    rows[i] = [0] * (4 - len(non_zero)) + non_zero
    
        elif direction in (Keys.UP, Keys.DOWN):
            for j in range(4):
                # Extract non-zero tiles from column
                col = [rows[i][j] for i in range(4) if rows[i][j] != 0]
                if not col:
                    continue
                    
                # For DOWN: process tiles from bottom to top
                if direction == Keys.DOWN:
                    col.reverse()
                    
                # Merge adjacent tiles
                i = 0
                while i < len(col) - 1:
                    if col[i] == col[i+1]:
                        col[i] *= 2
                        col.pop(i+1)
                    i += 1
                    
                # Reverse back if needed
                if direction == Keys.DOWN:
                    col.reverse()
                    
                # Pad with zeros in correct positions
                if direction == Keys.UP:
                    padded_col = col + [0] * (4 - len(col))
                else:  # DOWN
                    padded_col = [0] * (4 - len(col)) + col
                    
                # Update column
                for i in range(4):
                    rows[i][j] = padded_col[i]
                    
        return rows

    def is_move_valid(self, grid, direction):
        new_grid = self.simulate_move(grid, direction)
        return any(new_grid[i][j] != grid[i][j] 
                  for i in range(4) for j in range(4))
    
    def evaluate_grid(self, grid):
        """Heuristic evaluation of grid state"""
        # Weighting parameters
        weights = {
            'empty': 10.0,
            'monotonicity': 1.0,
            'smoothness': 0.1,
            'max_position': 100.0
        }
        
        # Count empty tiles
        empty = sum(row.count(0) for row in grid)
        
        # Find max tile and its position
        max_val = 0
        max_pos = (-1, -1)
        for i in range(4):
            for j in range(4):
                if grid[i][j] > max_val:
                    max_val = grid[i][j]
                    max_pos = (i, j)
        
        # Bonus for max tile in corner
        max_bonus = 1 if max_pos in [(0, 0), (0, 3), (3, 0), (3, 3)] else 0
        
        # Calculate monotonicity
        mono = 0
        for i in range(4):
            for j in range(3):
                if grid[i][j] >= grid[i][j+1]:
                    mono += 1
            for j in range(1, 4):
                if grid[i][j] >= grid[i][j-1]:
                    mono += 1
                    
        # Calculate smoothness (minimize adjacent differences)
        smooth = 0
        for i in range(4):
            for j in range(4):
                if j < 3:
                    smooth -= abs(grid[i][j] - grid[i][j+1])
                if i < 3:
                    smooth -= abs(grid[i][j] - grid[i+1][j])
        
        # Weighted sum of factors
        return (
            weights['empty'] * empty +
            weights['monotonicity'] * mono +
            weights['smoothness'] * smooth +
            weights['max_position'] * max_bonus
        )
    
    def expectimax_search(self, grid, depth, move=False):
        """Expectimax algorithm with configurable depth"""
        if depth == 0:
            return self.evaluate_grid(grid)
        
        if move:  # Player's move
            best_score = float('-inf')
            for direction in [Keys.LEFT, Keys.RIGHT, Keys.UP, Keys.DOWN]:
                new_grid = self.simulate_move(grid, direction)
                if new_grid == grid:
                    continue  # Skip invalid moves
                score = self.expectimax_search(new_grid, depth-1, False)
                if score > best_score:
                    best_score = score
            return best_score if best_score != float('-inf') else self.evaluate_grid(grid)
        
        else:  # Random tile placement (chance node)
            empty_cells = []
            for i in range(4):
                for j in range(4):
                    if grid[i][j] == 0:
                        empty_cells.append((i, j))
            
            if not empty_cells:
                return self.evaluate_grid(grid)
                
            total_score = 0
            # For each empty cell, consider both 2 and 4 possibilities
            for (i, j) in empty_cells:
                # Try 2 (90% probability)
                grid[i][j] = 2
                total_score += 0.9 * self.expectimax_search(grid, depth-1, True)
                
                # Try 4 (10% probability)
                grid[i][j] = 4
                total_score += 0.1 * self.expectimax_search(grid, depth-1, True)
                
                # Reset cell
                grid[i][j] = 0
                
            return total_score / len(empty_cells)
    
    def get_best_move(self):
        """Determine best move using expectimax algorithm"""
        grid = self.get_grid()
        best_score = float('-inf')
        best_move = None
        
        for direction in [Keys.LEFT, Keys.RIGHT, Keys.UP, Keys.DOWN]:
            new_grid = self.simulate_move(grid, direction)
            if new_grid == grid:
                continue  # Skip invalid moves
                
            # Evaluate move
            move_score = self.expectimax_search(new_grid, self.max_depth, False)
            if move_score > best_score:
                best_score = move_score
                best_move = direction
                
        return best_move if best_move is not None else Keys.LEFT  # Default if no valid moves

    def play_game(self):
    
        while True:
            time.sleep(0.15)
            grid = self.get_grid()
            possible_moves = [d for d in [Keys.UP, Keys.DOWN, Keys.LEFT, Keys.RIGHT] 
                             if self.is_move_valid(grid, d)]
        
            if not possible_moves:
                print(grid)
                time.sleep(40)
                print("Game Over!")
                break
            
            best_move = self.get_best_move()
            self.make_move(best_move)

# Initialize and run the AI
driver = webdriver.Chrome()
driver.get("http://wildcryptokid.com/2048/game/hardcore")

try:
    ai = GameAI(driver)
    ai.play_game()
finally:
    driver.quit()


