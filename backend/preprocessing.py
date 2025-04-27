import re
from bs4 import BeautifulSoup
try:
    from email_reply_parser import EmailReplyParser
except ImportError:
    EmailReplyParser = None

def deduplicate_emails(emails):
    """
    Remove duplicate emails from a list based on their ID.
    
    Args:
        emails (list): List of email dictionaries
        
    Returns:
        list: Deduplicated list of emails
    """
    unique_emails = {}
    for email in emails:
        if 'id' in email and email['id'] not in unique_emails:
            unique_emails[email['id']] = email
    
    return list(unique_emails.values())

def preprocess_email(text):
    """
    Clean email text by:
    - Removing HTML tags
    - Removing quoted replies/forwards
    - Removing signatures
    - Removing boilerplate content the user didn't write
    """
    # Return empty string if text is None or empty
    if not text:
        return ""
        
    # 1. Remove HTML tags
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()

    # 2. Remove quoted text (replies/forwards)
    if EmailReplyParser is not None:
        # Use EmailReplyParser for sophisticated reply detection
        parsed_text = EmailReplyParser.parse_reply(text)
        # If the parser returned something meaningful, use it
        if parsed_text and len(parsed_text.strip()) > 0:
            text = parsed_text
    
    # Apply additional cleaning regardless of EmailReplyParser
    
    # Remove lines starting with '>' (quoted text)
    text = re.sub(r"^>.*$", "", text, flags=re.MULTILINE)
    
    # Remove common forwarded content markers
    forward_patterns = [
        r"(?i)(-+\s*Forwarded message\s*-+).*?(-+\s*End forwarded message\s*-+)",
        r"(?i)(From:.*?Sent:.*?To:.*?Subject:.*?\n)",
        r"(?i)(On\s+.*?wrote:)",
        r"(?i)(Begin forwarded message:)",
        r"(?i)(Original Message\s*-+)",
        r"(?i)(From:.*?\[mailto:.*?\].*?Sent:.*?To:.*?Subject:.*?\n)"
    ]
    
    for pattern in forward_patterns:
        text = re.sub(pattern, "", text, flags=re.MULTILINE | re.DOTALL)
    
    # Remove text after common reply line markers
    reply_markers = [
        r"(?i)(On\s+.*?,.*?wrote:)",
        r"(?i)(On\s+.*?at\s+.*?,\s+.*?wrote:)",
        r"(?i)(From:.*?Sent:.*?To:.*?Subject:.*?\n)",
        r"(?i)(From:.*?<.*?>.*?Date:.*?Subject:.*?\n)",
        r"(?i)(On.*?,.*?<.*?>.*?wrote:)",
        r"(?i)(-----Original Message-----)",
        r"(?i)(Le.*?a écrit :)"
    ]
    
    for marker in reply_markers:
        parts = re.split(marker, text, maxsplit=1, flags=re.DOTALL)
        if len(parts) > 1:
            text = parts[0]

    # 3. Remove common signature blocks
    signature_patterns = [
        r"(?i)(-- ?\n.*$)",  # -- \n signature
        r"(?i)(^Sent from my .*$)",
        r"(?i)(^Best regards,.*$)",
        r"(?i)(^Kind regards,.*$)",
        r"(?i)(^Sincerely,.*$)",
        r"(?i)(^Cheers,.*$)",
        r"(?i)(^Thanks,.*$)",
        r"(?i)(^Thank you,.*$)",
        r"(?i)(^Many thanks,.*$)",
        r"(?i)(^Regards,.*$)",
        r"(?i)(^Met vriendelijke groet,.*$)",
        r"(?i)(^Mit freundlichen Grüßen,.*$)",
    ]
    
    for pat in signature_patterns:
        parts = re.split(pat, text, maxsplit=1, flags=re.MULTILINE | re.DOTALL)
        if len(parts) > 1:
            text = parts[0]
    
    # Clean up empty lines and whitespace
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = text.strip()
    
    return text 