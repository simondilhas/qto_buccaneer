def fill_text_line(text: str, width: int = 80, fill_char: str = " ") -> str:
    """
    Fill a text line to a specific width with a fill character.
    
    Args:
        text (str): The text to fill
        width (int): The total width of the line
        fill_char (str): The character to use for filling
        
    Returns:
        str: The filled text line
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

def format_definition_line(term: str, definition: str, width: int = 80) -> str:
    """
    Format a definition line with the term and definition.
    
    Args:
        term (str): The term being defined
        definition (str): The definition of the term
        width (int): The total width of the line
        
    Returns:
        str: The formatted definition line
    """
    # Create the line with term and definition
    line = f"{term}: {definition}"
    return fill_text_line(line, width)

def format_disclaimer(disclaimer: str, width: int = 80) -> str:
    """
    Format the disclaimer text.
    
    Args:
        disclaimer (str): The disclaimer text
        width (int): The total width of the line
        
    Returns:
        str: The formatted disclaimer
    """
    return fill_text_line(disclaimer, width) 