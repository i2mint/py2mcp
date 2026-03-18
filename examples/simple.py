"""
Simple example of py2mcp.

This example shows how to create an MCP server from regular Python functions.

To run this server:
    python examples/simple.py

To test with the MCP inspector:
    fastmcp dev examples/simple.py

To use with Claude Desktop, add to your config:
    {
      "mcpServers": {
        "simple": {
          "command": "python",
          "args": ["/path/to/examples/simple.py"]
        }
      }
    }
"""

from py2mcp import mk_mcp_server


def add(a: int, b: int) -> int:
    """Add two numbers together.
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        The sum of a and b
    """
    return a + b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers.
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        The product of a and b
    """
    return a * b


def greet(name: str = "world") -> str:
    """Generate a greeting message.
    
    Args:
        name: Name to greet (default: "world")
    
    Returns:
        A friendly greeting
    """
    return f"Hello, {name}!"


def is_even(n: int) -> bool:
    """Check if a number is even.
    
    Args:
        n: Number to check
    
    Returns:
        True if n is even, False otherwise
    """
    return n % 2 == 0


# Create MCP server with all our functions
mcp = mk_mcp_server(
    [add, multiply, greet, is_even],
    name="Simple Demo"
)


if __name__ == '__main__':
    # Run the server
    mcp.run()
