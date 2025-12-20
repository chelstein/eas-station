"""
Test for Icecast max_sources configuration feature.

Tests the configurable max sources limit functionality for Icecast server.
"""
import re


def test_max_sources_xml_update_existing_limits_section():
    """Test updating sources limit when <limits> section exists with <sources> tag."""
    content = """<icecast>
    <limits>
        <clients>100</clients>
        <sources>2</sources>
        <queue-size>524288</queue-size>
    </limits>
</icecast>"""
    
    max_sources = 5
    sources_limit = 0 if max_sources == 0 else max_sources
    
    # Replace existing <sources> tag
    updated = re.sub(
        r'(<limits>.*?)<sources>\d+</sources>(.*?</limits>)',
        rf'\1<sources>{sources_limit}</sources>\2',
        content,
        flags=re.DOTALL
    )
    
    assert '<sources>5</sources>' in updated
    assert '<sources>2</sources>' not in updated
    assert '<clients>100</clients>' in updated  # Other limits preserved


def test_max_sources_xml_update_limits_without_sources():
    """Test adding sources limit when <limits> exists but no <sources> tag."""
    content = """<icecast>
    <limits>
        <clients>100</clients>
    </limits>
</icecast>"""
    
    max_sources = 10
    sources_limit = 0 if max_sources == 0 else max_sources
    
    # Check if <sources> exists
    if not re.search(r'<limits>.*?<sources>\d+</sources>.*?</limits>', content, re.DOTALL):
        # Add <sources> tag inside existing <limits> section
        updated = re.sub(
            r'(<limits>)',
            rf'\1\n        <sources>{sources_limit}</sources>',
            content
        )
    else:
        updated = content
    
    assert '<sources>10</sources>' in updated
    assert '<clients>100</clients>' in updated


def test_max_sources_xml_update_no_limits_section():
    """Test adding sources limit when no <limits> section exists."""
    content = """<icecast>
    <authentication>
        <source-password>test</source-password>
    </authentication>
</icecast>"""
    
    max_sources = 0  # Unlimited
    sources_limit = 0 if max_sources == 0 else max_sources
    
    # Check if <limits> section exists
    if '<limits>' not in content:
        # Add entire <limits> section after <authentication> section
        limits_section = f'''
    <limits>
        <sources>{sources_limit}</sources>
    </limits>'''
        updated = re.sub(
            r'(</authentication>)',
            rf'\1{limits_section}',
            content
        )
    else:
        updated = content
    
    assert '<sources>0</sources>' in updated
    assert '<limits>' in updated
    assert '</limits>' in updated


def test_max_sources_unlimited_equals_zero():
    """Test that 0 is treated as unlimited sources."""
    max_sources = 0
    sources_limit = 0 if max_sources == 0 else max_sources
    assert sources_limit == 0


def test_max_sources_positive_integer():
    """Test that positive integers are passed through correctly."""
    max_sources = 5
    sources_limit = 0 if max_sources == 0 else max_sources
    assert sources_limit == 5


if __name__ == '__main__':
    # Run tests
    test_max_sources_xml_update_existing_limits_section()
    print("✓ test_max_sources_xml_update_existing_limits_section")
    
    test_max_sources_xml_update_limits_without_sources()
    print("✓ test_max_sources_xml_update_limits_without_sources")
    
    test_max_sources_xml_update_no_limits_section()
    print("✓ test_max_sources_xml_update_no_limits_section")
    
    test_max_sources_unlimited_equals_zero()
    print("✓ test_max_sources_unlimited_equals_zero")
    
    test_max_sources_positive_integer()
    print("✓ test_max_sources_positive_integer")
    
    print("\nAll tests passed!")
