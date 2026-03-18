"""
Example demonstrating input transformations with py2mcp.

This shows how to transform inputs before they reach your functions,
similar to the pattern used in qh (the HTTP version).

To run:
    python examples/transformations.py
"""

from py2mcp import mk_mcp_server, mk_input_trans


def add_arrays(a, b):
    """Add two arrays element-wise.
    
    Note: This function expects numpy arrays as inputs,
    but the MCP client will send lists. We use input_trans
    to convert lists to arrays automatically.
    
    Args:
        a: First array
        b: Second array
    
    Returns:
        List of summed elements
    """
    # Assumes a and b are numpy arrays (thanks to input_trans)
    return (a + b).tolist()


def normalize_vector(v):
    """Normalize a vector to unit length.
    
    Args:
        v: Vector as a list
    
    Returns:
        Normalized vector as a list
    """
    # v is converted to numpy array by input_trans
    import numpy as np
    norm = np.linalg.norm(v)
    if norm == 0:
        return v.tolist()
    return (v / norm).tolist()


def format_text(text: str, uppercase: bool = False) -> str:
    """Format text with optional uppercase conversion.
    
    This function doesn't need transformation - it works with plain types.
    
    Args:
        text: Text to format
        uppercase: Whether to convert to uppercase
    
    Returns:
        Formatted text
    """
    result = text.strip()
    if uppercase:
        result = result.upper()
    return result


# Try importing numpy - this is optional for the example
try:
    import numpy as np
    
    # Create input transformation for numpy functions
    # This converts specific parameters from lists to numpy arrays
    input_trans = mk_input_trans({
        'a': np.array,
        'b': np.array,
        'v': np.array,
    })
    
    # Create server with transformations
    mcp = mk_mcp_server(
        [add_arrays, normalize_vector, format_text],
        name="Transformations Demo",
        input_trans=input_trans
    )
    
    if __name__ == '__main__':
        print("Starting MCP server with numpy transformations...")
        print("Functions available:")
        print("  - add_arrays: Add two arrays element-wise")
        print("  - normalize_vector: Normalize a vector")
        print("  - format_text: Format text (no transformation needed)")
        mcp.run()
        
except ImportError:
    print("NumPy not installed. Install it with: pip install numpy")
    print("This example requires numpy for array operations.")
