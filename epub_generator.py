# -*- coding: utf-8 -*-
import os
import logging
try:
    from ebooklib import epub
except ImportError:
    logging.error("EbookLib is not installed. Please run 'pip install EbookLib'")
    raise

def create_epub_from_log(log_path, output_path=None, title="Log Export", author="Unknown"):
    """
    Reads a log file and converts each line into a paragraph in an EPUB file.
    
    Args:
        log_path (str): Path to the source log file.
        output_path (str, optional): Path to save the .epub file. 
                                     If None, replaces .log extension with .epub.
        title (str): Title of the EPUB book.
        author (str): Author of the EPUB book.
        
    Returns:
        str: The path of the generated EPUB file, or None if failed.
    """
    if not os.path.exists(log_path):
        logging.error(f"File not found: {log_path}")
        return None

    # Determine output path
    if output_path is None:
        base_name = os.path.splitext(log_path)[0]
        output_path = f"{base_name}.epub"

    try:
        # 1. Setup EPUB Metadata
        book = epub.EpubBook()
        book.set_identifier(os.path.basename(log_path))
        book.set_title(title)
        book.set_language('ko')
        book.add_author(author)

        # 2. Read Log File
        lines = []
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]

        if not lines:
            logging.warning("Log file is empty. No EPUB created.")
            return None

        # 3. Create Content Chapter
        c1 = epub.EpubHtml(title='Content', file_name='content.xhtml', lang='ko')
        
        # Convert lines to HTML paragraphs
        content_html = "<h1>Log Content</h1>"
        for line in lines:
            # Simple escaping for HTML safety could be added here if needed
            content_html += f"<p>{line}</p>\n"
            
        c1.content = content_html

        # Add chapter to book
        book.add_item(c1)

        # 4. Define Table of Contents and Spine
        book.toc = (epub.Link('content.xhtml', 'Content', 'intro'), c1)
        
        # Add default NCX and Nav file
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Define CSS style
        style = 'body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; } p { margin-bottom: 1em; }'
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        book.add_item(nav_css)

        # Set the spine (order of reading)
        book.spine = ['nav', c1]

        # 5. Write EPUB file
        epub.write_epub(output_path, book, {})
        logging.info(f"EPUB successfully created at: {output_path}")
        
        return output_path

    except Exception as e:
        logging.error(f"Failed to create EPUB: {e}")
        return None

if __name__ == "__main__":
    # Test execution
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
        create_epub_from_log(log_file)
    else:
        print("Usage: python epub_generator.py <path_to_log_file>")
