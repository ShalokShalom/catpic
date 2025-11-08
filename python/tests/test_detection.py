# Destination: tests/test_detection.py

"""
Tests for terminal capability detection.
"""

import os
import pytest
from unittest.mock import patch

from catpic.detection import (
    CapabilityDetector,
    TerminalCapability,
    detect_best_protocol,
    supports_protocol,
)


class TestKittyDetection:
    """Test Kitty terminal detection."""
    
    def test_detect_via_window_id(self):
        """Kitty detected via KITTY_WINDOW_ID env var."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {'KITTY_WINDOW_ID': '1'}):
            assert detector._detect_kitty() is True
    
    def test_detect_via_term(self):
        """Kitty detected via $TERM."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {'TERM': 'xterm-kitty'}, clear=True):
            assert detector._detect_kitty() is True
    
    def test_detect_through_tmux(self):
        """Kitty detected through tmux with KITTY_WINDOW_ID."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {
            'TERM': 'tmux-256color',
            'TERM_PROGRAM': 'tmux',
            'KITTY_WINDOW_ID': '1',
        }, clear=True):
            assert detector._detect_kitty() is True
    
    def test_not_detected(self):
        """Kitty not detected without indicators."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {}, clear=True):
            assert detector._detect_kitty() is False


class TestSixelDetection:
    """Test Sixel graphics detection."""
    
    @pytest.mark.parametrize('term', [
        'xterm',
        'xterm-256color',
        'mlterm',
        'foot',
        'mintty',
    ])
    def test_detect_via_term(self, term):
        """Sixel detected via known $TERM values."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {'TERM': term}, clear=True):
            assert detector._detect_sixel() is True
    
    def test_detect_wezterm(self):
        """Wezterm detected via exact TERM match."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {'TERM': 'wezterm'}, clear=True):
            assert detector._detect_sixel() is True
    
    def test_detect_through_tmux_vte(self):
        """Sixel detected through tmux with VTE terminal."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {
            'TERM': 'tmux-256color',
            'TMUX': '/tmp/tmux-1000/default,12345,0',  # Typical TMUX value
            'VTE_VERSION': '7400',
        }, clear=True):
            assert detector._detect_sixel() is True
    
    def test_not_detected(self):
        """Sixel not detected for unknown terminals."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {'TERM': 'unknown'}, clear=True):
            assert detector._detect_sixel() is False


class TestITerm2Detection:
    """Test iTerm2 inline images detection."""
    
    def test_detect_via_term_program(self):
        """iTerm2 detected via TERM_PROGRAM."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {'TERM_PROGRAM': 'iTerm.app'}, clear=True):
            assert detector._detect_iterm2() is True
    
    def test_detect_via_lc_terminal(self):
        """iTerm2 detected via LC_TERMINAL."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {'LC_TERMINAL': 'iTerm2'}, clear=True):
            assert detector._detect_iterm2() is True
    
    def test_not_detected(self):
        """iTerm2 not detected without indicators."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {}, clear=True):
            assert detector._detect_iterm2() is False


class TestCapabilityDetector:
    """Test overall capability detection."""
    
    def test_always_includes_glyxel(self):
        """Glyxel is always available as fallback."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {}, clear=True):
            caps = detector.detect_capabilities(use_cache=False)
            assert TerminalCapability.GLYXEL in caps
    
    def test_kitty_first_priority(self):
        """Kitty is highest priority when available."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {'KITTY_WINDOW_ID': '1'}, clear=True):
            caps = detector.detect_capabilities(use_cache=False)
            assert caps[0] == TerminalCapability.KITTY
    
    def test_caching(self):
        """Detection results are cached."""
        detector = CapabilityDetector()
        
        # First call with Kitty
        with patch.dict(os.environ, {'KITTY_WINDOW_ID': '1'}, clear=True):
            caps1 = detector.detect_capabilities(use_cache=False)
            assert TerminalCapability.KITTY in caps1
        
        # Second call with cache (should still have Kitty even though env changed)
        with patch.dict(os.environ, {}, clear=True):
            caps2 = detector.detect_capabilities(use_cache=True)
            assert caps1 == caps2  # Same cached result
            
            # Force refresh
            caps3 = detector.detect_capabilities(use_cache=False)
            assert TerminalCapability.KITTY not in caps3  # New detection
    
    def test_select_best_protocol(self):
        """select_best_protocol returns highest priority."""
        detector = CapabilityDetector()
        
        # Kitty environment
        with patch.dict(os.environ, {'KITTY_WINDOW_ID': '1'}, clear=True):
            assert detector.select_best_protocol() == 'kitty'
        
        # No special terminal
        detector._cache = None  # Clear cache
        with patch.dict(os.environ, {}, clear=True):
            assert detector.select_best_protocol() == 'glyxel'
    
    def test_supports_protocol(self):
        """supports_protocol checks for specific protocol."""
        detector = CapabilityDetector()
        
        with patch.dict(os.environ, {'KITTY_WINDOW_ID': '1'}, clear=True):
            detector._cache = None
            assert detector.supports_protocol('kitty') is True
            assert detector.supports_protocol('glyxel') is True
            assert detector.supports_protocol('invalid') is False


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_detect_best_protocol(self):
        """detect_best_protocol works."""
        with patch.dict(os.environ, {'KITTY_WINDOW_ID': '1'}, clear=True):
            # Clear any existing detector
            import catpic.detection
            catpic.detection._detector = None
            
            protocol = detect_best_protocol()
            assert protocol == 'kitty'
    
    def test_supports_protocol(self):
        """supports_protocol works."""
        with patch.dict(os.environ, {'KITTY_WINDOW_ID': '1'}, clear=True):
            # Clear any existing detector
            import catpic.detection
            catpic.detection._detector = None
            
            assert supports_protocol('kitty') is True
            assert supports_protocol('glyxel') is True
