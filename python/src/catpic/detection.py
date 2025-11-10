# Destination: src/catpic/detection.py

"""
Terminal capability detection for protocol selection.

Detects which graphics protocols the terminal supports and selects
the best available option with graceful fallback to glyxel.

Detection methods (in priority order):
1. Environment variables (most reliable)
2. Terminal queries (universal but requires terminal interaction)
3. $TERM heuristics (fallback)
"""

import os
import sys
import select
from typing import Optional, List
from enum import Enum


class TerminalCapability(Enum):
    """Supported terminal graphics protocols."""
    KITTY = "kitty"
    SIXEL = "sixel"
    ITERM2 = "iterm2"
    GLYXEL = "glyxel"  # Universal fallback


class CapabilityDetector:
    """
    Detect terminal graphics protocol support.
    
    Uses multiple detection methods with caching to avoid
    redundant terminal queries.
    """
    
    def __init__(self):
        self._cache: Optional[List[TerminalCapability]] = None
    
    def detect_capabilities(self, use_cache: bool = True) -> List[TerminalCapability]:
        """
        Detect all supported capabilities.
        
        Args:
            use_cache: Use cached result if available
            
        Returns:
            List of supported capabilities in priority order
        """
        if use_cache and self._cache is not None:
            return self._cache
        
        capabilities = []
        
        # Detect specific protocols
        if self._detect_kitty():
            capabilities.append(TerminalCapability.KITTY)
        
        if self._detect_sixel():
            capabilities.append(TerminalCapability.SIXEL)
        
        if self._detect_iterm2():
            capabilities.append(TerminalCapability.ITERM2)
        
        # Glyxel is always available as fallback
        capabilities.append(TerminalCapability.GLYXEL)
        
        self._cache = capabilities
        return capabilities
    
    def select_best_protocol(self) -> str:
        """
        Select the best available protocol.
        
        Returns:
            Protocol name suitable for use with get_generator()
        """
        capabilities = self.detect_capabilities()
        
        # Return the first (best) capability
        return capabilities[0].value
    
    def supports_protocol(self, protocol: str) -> bool:
        """
        Check if a specific protocol is supported.
        
        Args:
            protocol: Protocol name ('kitty', 'sixel', 'iterm2', 'glyxel')
            
        Returns:
            True if supported
        """
        capabilities = self.detect_capabilities()
        
        try:
            cap = TerminalCapability(protocol)
            return cap in capabilities
        except ValueError:
            return False
    
    # ========================================================================
    # Protocol-Specific Detection
    # ========================================================================
    
    def _detect_kitty(self) -> bool:
        """
        Detect Kitty terminal graphics support.
        
        Detection methods:
        1. KITTY_WINDOW_ID environment variable (most reliable)
        2. $TERM contains 'kitty'
        3. Check through tmux if present
        
        Returns:
            True if Kitty graphics are supported
        """
        # Method 1: Environment variable (definitive)
        if os.getenv('KITTY_WINDOW_ID'):
            return True
        
        # Method 2: $TERM heuristic
        term = os.getenv('TERM', '')
        if 'kitty' in term.lower():
            return True
        
        # Method 3: Check through tmux
        # Tmux can passthrough graphics if the underlying terminal supports it
        if self._is_inside_tmux():
            # Check if underlying terminal is Kitty
            # KITTY_WINDOW_ID survives tmux in many cases
            if os.getenv('KITTY_WINDOW_ID'):
                return True
            
            # Check TERM_PROGRAM from outside tmux (some configs preserve this)
            term_program = os.getenv('TERM_PROGRAM', '')
            if 'kitty' in term_program.lower():
                return True
        
        return False
    
    def _detect_sixel(self) -> bool:
        """
        Detect Sixel graphics support.
        
        Detection methods:
        1. $TERM heuristics (xterm-*, mlterm, foot, etc.)
        2. Check through tmux if present
        3. Terminal query DA1 response (future)
        
        Returns:
            True if Sixel is supported
        """
        term = os.getenv('TERM', '')
        
        # Known Sixel-capable terminals
        sixel_terms = [
            'xterm',
            'mlterm',
            'foot',
            'yaft',
            'mintty',
        ]
        
        # Note: wezterm in term list but checking separately
        # because $TERM is usually just "wezterm" not "xterm-wezterm"
        for sixel_term in sixel_terms:
            if sixel_term in term.lower():
                return True
        
        # Check for wezterm specifically (exact match)
        if term.lower() == 'wezterm':
            return True
        
        # Check through tmux
        if self._is_inside_tmux():
            # Some terminals preserve enough info to detect
            # Check VTE_VERSION for VTE-based terminals (gnome-terminal, xfce4-terminal)
            if os.getenv('VTE_VERSION'):
                return True
            
            # Check for other indicators
            term_program = os.getenv('TERM_PROGRAM', '')
            if any(t in term_program.lower() for t in sixel_terms):
                return True
            
            # Check if wezterm is the underlying terminal
            if 'wezterm' in term_program.lower():
                return True
        
        return False
    
    def _is_inside_tmux(self) -> bool:
        """Check if running inside tmux."""
        # Check both TERM_PROGRAM and TMUX variable
        # TMUX is set by tmux itself, TERM_PROGRAM might be set by some configs
        return os.getenv('TMUX') is not None or os.getenv('TERM_PROGRAM') == 'tmux'
    
    def _detect_iterm2(self) -> bool:
        """
        Detect iTerm2 inline images support.
        
        Detection methods:
        1. TERM_PROGRAM environment variable
        2. $TERM heuristics
        
        Returns:
            True if iTerm2 inline images are supported
        """
        # Method 1: TERM_PROGRAM (most reliable for iTerm2)
        term_program = os.getenv('TERM_PROGRAM', '')
        if term_program == 'iTerm.app':
            return True
        
        # Method 2: LC_TERMINAL (alternative env var)
        lc_terminal = os.getenv('LC_TERMINAL', '')
        if lc_terminal == 'iTerm2':
            return True
        
        return False
    
    # ========================================================================
    # Terminal Query Utilities (Future Use)
    # ========================================================================
    
    def _query_terminal(self, query: bytes, timeout: float = 0.1) -> Optional[bytes]:
        """
        Send a query to the terminal and read response.
        
        This is a foundation for future terminal queries but is not
        currently used to avoid blocking on non-interactive terminals.
        
        Args:
            query: Escape sequence to send
            timeout: Max time to wait for response (seconds)
            
        Returns:
            Terminal response or None if timeout/not a tty
        """
        # Only works on interactive terminals
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return None
        
        try:
            # Save terminal state
            import termios
            import tty
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            
            try:
                # Set raw mode for reading response
                tty.setraw(fd)
                
                # Send query
                sys.stdout.buffer.write(query)
                sys.stdout.buffer.flush()
                
                # Wait for response with timeout
                if select.select([sys.stdin], [], [], timeout)[0]:
                    response = sys.stdin.buffer.read(1024)
                    return response
                
                return None
                
            finally:
                # Restore terminal state
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
        except (ImportError, OSError, termios.error):
            # Not available on this platform or not a terminal
            return None


# Global detector instance (singleton pattern)
_detector: Optional[CapabilityDetector] = None


def get_detector() -> CapabilityDetector:
    """Get the global capability detector instance."""
    global _detector
    if _detector is None:
        _detector = CapabilityDetector()
    return _detector


def detect_best_protocol() -> str:
    """
    Convenience function to detect the best available protocol.
    
    Checks CATPIC_CONFIG for user override, then auto-detects.
    
    Returns:
        Protocol name suitable for use with get_generator()
    """
    # Check for user override via config
    try:
        from .config import load_config
        config = load_config()
        protocol = config.get('protocol', 'auto')
        
        if protocol and protocol != 'auto':
            # Validate it's supported
            detector = get_detector()
            if detector.supports_protocol(protocol):
                return protocol
            # If invalid, fall through to auto-detection
    except Exception:
        # Config loading failed, fall through to auto-detection
        pass
    
    return get_detector().select_best_protocol()


def supports_protocol(protocol: str) -> bool:
    """
    Convenience function to check protocol support.
    
    Args:
        protocol: Protocol name to check
        
    Returns:
        True if the protocol is supported
    """
    return get_detector().supports_protocol(protocol)
