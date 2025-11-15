# Destination: src/catpic/renderer.py

"""
Layer rendering with timing support.

Handles rendering sequences of layers with frame timing, looping,
and protocol-aware animation.
"""

import time
import sys
from typing import List, Dict, Any, Optional

from .framebuffer import FrameBuffer


class LayerRenderer:
    """
    Renders layer sequences with timing and protocol awareness.
    
    Supports:
    - Frame timing (render_at_ms)
    - Looping (0=forever, 1=once, N=N times)
    - Protocol-aware animation (uses native protocols for frame sequences)
    - Cursor management (reserves space, saves position for animation)
    - External frame sources (games, video, emulators)
    """
    
    def __init__(self, framebuffer: FrameBuffer):
        """
        Initialize renderer with framebuffer.
        
        Args:
            framebuffer: FrameBuffer instance for display
        """
        self.fb = framebuffer
        self._cursor_saved = False
    
    def setup_animation_canvas(self, height: int) -> None:
        """
        Setup canvas for animation by reserving space and saving cursor.
        
        This establishes the animation origin point. All frames will be
        rendered relative to this saved position.
        
        Args:
            height: Canvas height in rows (for space reservation)
        """
        # Hide cursor for animation
        sys.stdout.write('\x1b[?25l')
        # Reserve vertical space (scroll terminal)
        sys.stdout.write('\n' * height)
        # Move up to canvas top
        sys.stdout.write(f'\x1b[{height}A')
        # Save cursor at canvas origin
        sys.stdout.write('\x1b[s')
        sys.stdout.flush()
        self._cursor_saved = True
    
    def teardown_animation_canvas(self, height: int) -> None:
        """
        Teardown animation canvas by restoring cursor and moving below.
        
        Protocol-aware positioning accounts for different cursor behavior:
        - Glyxel: Cursor at end of last line (inline text)
        - Image protocols: Cursor at start of new line (auto-advance after image)
        
        Args:
            height: Canvas height in rows
        """
        if self._cursor_saved:
            # Restore cursor to saved position (top of canvas)
            sys.stdout.write('\x1b[u')
            
            # Protocol-specific cursor positioning
            if self.fb.protocol_name == 'glyxel':
                # Glyxel renders inline text - cursor at end of last line
                # Move down height lines to position below canvas
                sys.stdout.write(f'\x1b[{height}B')
            else:
                # Image protocols (kitty, sixel, iterm2) auto-advance cursor
                # After rendering, cursor is already at start of new line
                # Move down (height - 1) to avoid extra blank line
                if height > 1:
                    sys.stdout.write(f'\x1b[{height - 1}B')
                # else: already at correct position (single-line image)
            
            # Show cursor
            sys.stdout.write('\x1b[?25h')
            sys.stdout.flush()
            self._cursor_saved = False
    
    def render_layer(self, layer_data: bytes, clear_previous: bool = False) -> None:
        """
        Render single layer to framebuffer.
        
        Args:
            layer_data: PNG-encoded image data
            clear_previous: Whether to restore cursor before rendering
        """
        if clear_previous and self._cursor_saved:
            # Restore cursor to saved position (animation frame replacement)
            sys.stdout.write('\x1b[u')
            sys.stdout.flush()
        
        self.fb.render(layer_data)
    
    def render_sequence(self, layers: List[Dict[str, Any]], clear_between_frames: bool = True) -> None:
        """
        Render sequence of layers respecting timing.
        
        Args:
            layers: List of layer dicts with 'data' and optional 'render_at_ms'
            clear_between_frames: Clear display between frames (for animation)
        """
        if not layers:
            return
        
        start_time = self._time_ms()
        
        for i, layer in enumerate(layers):
            # Calculate target time
            target_ms = layer.get('render_at_ms', 0)
            target_time = start_time + target_ms
            
            # Wait until target time
            current_time = self._time_ms()
            if current_time < target_time:
                wait_ms = target_time - current_time
                time.sleep(wait_ms / 1000.0)
            
            # For animation, restore cursor before ALL frames (including first)
            should_clear = clear_between_frames and self._cursor_saved
            
            # Render layer
            self.render_layer(layer['data'], clear_previous=should_clear)
    
    def render_with_loop(self, layers: List[Dict[str, Any]], loop_count: int = 1) -> None:
        """
        Render layers with looping support.
        
        Args:
            layers: List of layer dicts
            loop_count: How many times to loop (0=forever, 1=once, N=N times)
        """
        if not layers:
            return
        
        # Determine if this is animation (needs clearing between frames)
        is_animation = len(layers) > 1 or loop_count != 1
        
        if loop_count == 0:
            # Infinite loop
            try:
                while True:
                    self.render_sequence(layers, clear_between_frames=is_animation)
            except KeyboardInterrupt:
                # Allow clean exit from infinite loop
                sys.stderr.write('\n')
                return
        else:
            # Fixed loop count
            for _ in range(loop_count):
                self.render_sequence(layers, clear_between_frames=is_animation)
    
    def _time_ms(self) -> float:
        """
        Get current time in milliseconds.
        
        Returns:
            Current time in milliseconds
        """
        return time.time() * 1000.0
