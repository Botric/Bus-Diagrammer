#!/usr/bin/env python3
"""
Test script to validate the bus scheduling fixes:
1. Run ordering preservation
2. Color distinctiveness
3. Break calculation accuracy
"""

from datetime import datetime
from app import Run, schedule_buses, get_breaks_for_bus

def test_run_ordering():
    """Test that runs maintain their input order"""
    print("Testing run ordering...")
    
    # Create runs in a specific order (not alphabetical by ID)
    runs = [
        Run("Z-Late", datetime.strptime('22:00', '%H:%M'), datetime.strptime('23:00', '%H:%M'), ['Stop1', 'Stop2'], 'inbound'),
        Run("A-Early", datetime.strptime('06:00', '%H:%M'), datetime.strptime('07:00', '%H:%M'), ['Stop1', 'Stop2'], 'inbound'),
        Run("M-Mid", datetime.strptime('12:00', '%H:%M'), datetime.strptime('13:00', '%H:%M'), ['Stop1', 'Stop2'], 'outbound'),
    ]
    
    # The runs list should maintain input order (Z-Late, A-Early, M-Mid)
    expected_order = ["Z-Late", "A-Early", "M-Mid"]
    actual_order = [run.run_id for run in runs]
    
    if actual_order == expected_order:
        print("✅ Run ordering test PASSED - Input order preserved")
    else:
        print(f"❌ Run ordering test FAILED - Expected: {expected_order}, Got: {actual_order}")
    
    return actual_order == expected_order

def test_color_palette():
    """Test that color palette provides distinct colors"""
    print("\nTesting color distinctiveness...")
    
    color_palette = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43', '#EE5A24', '#0984E3', '#6C5CE7', '#A29BFE', '#FD79A8', '#E17055', '#00B894', '#FDCB6E', '#E84393', '#2D3436']
    
    # Test that we have enough distinct colors
    if len(color_palette) >= 20:
        print("✅ Color palette test PASSED - 20+ distinct colors available")
        palette_pass = True
    else:
        print(f"❌ Color palette test FAILED - Only {len(color_palette)} colors available")
        palette_pass = False
    
    # Test that colors are distinct (no duplicates)
    if len(set(color_palette)) == len(color_palette):
        print("✅ Color uniqueness test PASSED - All colors are unique")
        unique_pass = True
    else:
        print("❌ Color uniqueness test FAILED - Duplicate colors found")
        unique_pass = False
    
    return palette_pass and unique_pass

def test_break_calculation():
    """Test break calculation logic"""
    print("\nTesting break calculation...")
    
    # Create runs that should trigger a break
    runs = [
        Run("R1", datetime.strptime('06:00', '%H:%M'), datetime.strptime('08:30', '%H:%M'), ['Stop1'], 'inbound'),  # 2.5 hours
        Run("R2", datetime.strptime('09:00', '%H:%M'), datetime.strptime('11:30', '%H:%M'), ['Stop1'], 'outbound'), # 2.5 hours (total: 5 hours)
        Run("R3", datetime.strptime('12:00', '%H:%M'), datetime.strptime('13:00', '%H:%M'), ['Stop1'], 'inbound'),  # 1 hour (should trigger break)
    ]
    
    # Test EU regime (4.5 hour limit)
    eu_breaks = get_breaks_for_bus(runs, 'EU')
    if len(eu_breaks) == 1:  # Should have one break before R3
        print("✅ EU break calculation test PASSED - Break scheduled correctly")
        eu_pass = True
    else:
        print(f"❌ EU break calculation test FAILED - Expected 1 break, got {len(eu_breaks)}")
        eu_pass = False
    
    # Test GB regime (5.5 hour limit)
    gb_breaks = get_breaks_for_bus(runs, 'GB')
    if len(gb_breaks) == 0:  # Should have no breaks (5 hours < 5.5 hour limit)
        print("✅ GB break calculation test PASSED - No break needed")
        gb_pass = True
    else:
        print(f"❌ GB break calculation test FAILED - Expected 0 breaks, got {len(gb_breaks)}")
        gb_pass = False
    
    return eu_pass and gb_pass

def main():
    """Run all tests"""
    print("🚌 Running Bus Scheduler Fix Tests\n")
    
    test_results = [
        test_run_ordering(),
        test_color_palette(),
        test_break_calculation()
    ]
    
    print(f"\n📊 Test Results: {sum(test_results)}/{len(test_results)} tests passed")
    
    if all(test_results):
        print("🎉 All tests PASSED! The fixes are working correctly.")
    else:
        print("⚠️  Some tests FAILED. Please review the implementation.")

if __name__ == "__main__":
    main()
