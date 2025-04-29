from typing import Optional
from weasyprint import HTML
from qto_buccaneer.reports import ReportStyleConfig

def _convert_html_to_pdf(
    html_content: str, 
    output_path: str,
    style_config: Optional[ReportStyleConfig] = None
) -> str:
    """
    Helper function to convert HTML content to PDF using WeasyPrint with styling.
    Used by generate_metrics_report() to handle PDF conversion.
    
    Args:
        html_content (str): HTML content to convert
        output_path (str): Path where the PDF should be saved
        style_config (Optional[ReportStyleConfig]): Configuration for report styling
        
    Returns:
        str: Path to the generated PDF file
        
    Raises:
        Exception: If PDF conversion fails
        
    Note:
        This is an internal helper function and should not be called directly.
        Use generate_metrics_report() instead.
    """
    try:
        # Use default config if none provided
        style_config = style_config or ReportStyleConfig()
        
        # Add CSS to HTML content
        css = style_config.to_css()
        html_with_css = f"""
            <style>
                {css}
            </style>
            {html_content}
        """
        
        HTML(string=html_with_css).write_pdf(output_path)
        return output_path
    except Exception as e:
        raise Exception(f"Failed to convert HTML to PDF: {str(e)}")
    
def _format_definition_line(term: str, definition: str, width: int = 80) -> str:
    """
    Helper function to format a definition line.
    Used by other functions for text formatting.
    
    Args:
        term (str): The term being defined
        definition (str): The definition of the term
        width (int): The total width of the line
        
    Returns:
        str: The formatted definition line
        
    Note:
        This is an internal helper function and should not be called directly.
        Use the appropriate public function instead.
    """
    # Create the line with term and definition
    line = f"{term}: {definition}"
    return _fill_text_line(line, width)

def _format_disclaimer(disclaimer: str, width: int = 80) -> str:
    """
    Helper function to format disclaimer text.
    Used by other functions for text formatting.
    
    Args:
        disclaimer (str): The disclaimer text
        width (int): The total width of the line
        
    Returns:
        str: The formatted disclaimer
        
    Note:
        This is an internal helper function and should not be called directly.
        Use the appropriate public function instead.
    """
    return _fill_text_line(disclaimer, width)

def _render_template_with_filled_text(template, context):
    """
    Helper function to render template with filled text.
    Used by other functions for template rendering.
    
    Args:
        template: The Jinja2 template
        context (dict): The context for the template
        
    Returns:
        str: The rendered template with filled text
        
    Note:
        This is an internal helper function and should not be called directly.
        Use the appropriate public function instead.
    """
    # Format definitions
    definitions = [
        ("Gross Floor Area (GFA)", "The total area of all floors in a building, measured from the exterior walls."),
        ("Gross Volume (GV)", "The total volume of the building, including all enclosed spaces."),
        ("Net Floor Area (NFA)", "The usable area within the building, excluding walls."),
        ("Net Volume (NV)", "The volume of usable space within the building."),
        ("Construction Area", "Difference between GFA and NFA."),
        ("Construction Volume", "Difference between GV and NV."),
        ("Facade Area (FA)", "The total exterior surface area of the building envelope."),
        ("Room Type", "A classification of rooms based on their intended function."),
        ("Spatial Relationships", "Position between elements (e.g., a window relating to a room)."),
        ("Storey", "A horizontal division of a building."),
        ("Baseplate", "The foundational slab at the bottom of the building."),
        ("Covering Area", "Area of facade elements like cladding and panels.")
    ]
    
    # Format each definition
    formatted_definitions = [
        _format_definition_line(term, definition)
        for term, definition in definitions
    ]
    
    # Format disclaimer
    disclaimer = "These quantities were generated automatically using the abstractBIM system. Accuracy depends on input quality. The general terms and conditions of abstract AG apply."
    formatted_disclaimer = _format_disclaimer(disclaimer)
    
    # Add formatted text to context
    context.update({
        'formatted_definitions': formatted_definitions,
        'formatted_disclaimer': formatted_disclaimer
    })
    
    return template.render(context)

def _fill_text_line(text: str, width: int = 80, fill_char: str = " ") -> str:
    """
    Helper function to fill a text line to a specific width.
    Used by other functions for text formatting.
    
    Args:
        text (str): The text to fill
        width (int): The total width of the line
        fill_char (str): The character to use for filling
        
    Returns:
        str: The filled text line
        
    Note:
        This is an internal helper function and should not be called directly.
        Use the appropriate public function instead.
    """
    if not text:
        return fill_char * width
        
    # Split text into words
    words = text.split()
    if not words:
        return fill_char * width
        
    # Start with the first word
    lines = [words[0]]
    current_length = len(words[0])
    
    # Add remaining words
    for word in words[1:]:
        # If adding the word would exceed the width, start a new line
        if current_length + len(word) + 1 > width:
            lines.append(word)
            current_length = len(word)
        else:
            # Add the word to the current line
            lines[-1] += " " + word
            current_length += len(word) + 1
            
    # Fill each line to the specified width
    filled_lines = []
    for line in lines:
        # Calculate how many fill characters to add
        fill_count = width - len(line)
        if fill_count > 0:
            filled_line = line + (fill_char * fill_count)
        else:
            filled_line = line
        filled_lines.append(filled_line)
        
    return "\n".join(filled_lines)