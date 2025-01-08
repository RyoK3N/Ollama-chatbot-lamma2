import pygame
import sys
import toml
import threading
from queue import Queue
from langchain_ollama import OllamaLLM
from langchain.callbacks.base import BaseCallbackHandler
import textwrap
import re
from pathlib import Path

# Load config
config = toml.load("config.toml")

# Initialize Pygame
pygame.init()
pygame.font.init()

# Constants
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
CHAT_AREA_HEIGHT = WINDOW_HEIGHT - 100
INPUT_HEIGHT = 60
PADDING = 20
MAX_LINE_LENGTH = 80
FONT_SIZE = 16
SCROLL_SPEED = 30
MESSAGE_SPACING = 20
BUBBLE_RADIUS = 15
LOADING_DOTS_INTERVAL = 500  # milliseconds between dots
MAX_LOADING_DOTS = 3

# Colors
THEME = {
    'background': (240, 242, 245),
    'user_bubble': (0, 132, 255),
    'assistant_bubble': (255, 255, 255),
    'user_text': (255, 255, 255),
    'assistant_text': (0, 0, 0),
    'input_bg': (255, 255, 255),
    'input_border': (220, 220, 220),
    'input_border_active': (0, 132, 255),
    'input_text': (0, 0, 0),
    'code_bg': (45, 45, 45),
    'code_text': (255, 255, 255),
    'scrollbar': (200, 200, 200),
    'scrollbar_hover': (180, 180, 180),
    'loading_color': (150, 150, 150),
    'loading_bubble': (245, 245, 245),
}

class StreamHandler(BaseCallbackHandler):
    """Handler for streaming LLM responses"""
    def __init__(self, response_queue):
        self.response_queue = response_queue
        self.current_response = ""
        self.is_complete = False
        print("DEBUG: StreamHandler initialized")

    def on_llm_start(self, *args, **kwargs):
        """Called when LLM starts processing"""
        print("DEBUG: LLM processing started")
        self.current_response = ""
        self.is_complete = False

    def on_llm_new_token(self, token: str, **kwargs):
        """Called when LLM produces a new token"""
        if token is None:
            print("DEBUG: Received None token")
            return
            
        print(f"DEBUG: New token received: '{token}'")
        if not self.is_complete:
            self.current_response += token
            print(f"DEBUG: Current response length: {len(self.current_response)}")
            if self.current_response.strip():
                print(f"DEBUG: Sending streaming response: '{self.current_response}'")
                self.response_queue.put(("streaming", self.current_response))

    def on_llm_end(self, *args, **kwargs):
        """Called when LLM response is complete"""
        print("DEBUG: LLM response complete")
        self.is_complete = True
        if self.current_response.strip():
            print(f"DEBUG: Sending final response: '{self.current_response}'")
            self.response_queue.put(("complete", self.current_response))
        else:
            print("DEBUG: No response to send at completion")

    def on_llm_error(self, error: Exception, **kwargs):
        """Called if LLM encounters an error"""
        print(f"DEBUG: LLM error occurred: {str(error)}")
        self.is_complete = True
        error_msg = f"Error: {str(error)}"
        print(f"DEBUG: Sending error message: '{error_msg}'")
        self.response_queue.put(("error", error_msg))

class ModernTextBox:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.active = False
        self.font = pygame.font.SysFont('Arial', 16)
        self.cursor_visible = True
        self.cursor_timer = 0
        self.padding = 10

    def draw(self, surface):
        # Draw background
        pygame.draw.rect(surface, THEME['input_bg'], self.rect, border_radius=10)
        
        # Draw border
        border_color = THEME['input_border_active'] if self.active else THEME['input_border']
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=10)

        # Draw text
        if self.text:
            text_surf = self.font.render(self.text, True, THEME['input_text'])
            text_rect = text_surf.get_rect(
                midleft=(self.rect.left + self.padding, self.rect.centery)
            )
            surface.blit(text_surf, text_rect)

        # Draw cursor
        self.cursor_timer += 1
        if self.active and self.cursor_timer // 30 % 2 == 0:
            text_width = self.font.size(self.text)[0]
            cursor_x = self.rect.left + self.padding + text_width
            pygame.draw.line(
                surface,
                THEME['input_text'],
                (cursor_x, self.rect.centery - 10),
                (cursor_x, self.rect.centery + 10),
                2
            )

class MessageBubble:
    def __init__(self, text, is_user, width):
        self.text = text
        self.is_user = is_user
        self.width = width - 100  # Padding for bubbles
        self.font = pygame.font.SysFont('Arial', 16)
        self.code_font = pygame.font.SysFont('Courier New', 16)
        self.rendered_surfaces = None
        self.height = 0
        self.render()

    def render(self):
        surfaces = []
        y_offset = 0
        
        # Split into regular text and code blocks
        parts = re.split(r'(```.*?```)', self.text, flags=re.DOTALL)
        
        for part in parts:
            if part.startswith('```') and part.endswith('```'):
                # Handle code block
                code_lines = part.strip('`').split('\n')[1:-1]  # Remove first and last lines
                code_surface = pygame.Surface((self.width - 20, len(code_lines) * 20))
                code_surface.fill(THEME['code_bg'])
                
                for i, line in enumerate(code_lines):
                    code_text = self.code_font.render(line, True, THEME['code_text'])
                    code_surface.blit(code_text, (10, i * 20))
                
                surfaces.append(('code', code_surface))
                y_offset += code_surface.get_height() + 10
            else:
                # Handle regular text
                words = part.split()
                lines = []
                current_line = []
                
                for word in words:
                    current_line.append(word)
                    text_width = self.font.size(' '.join(current_line))[0]
                    if text_width > self.width - 40:
                        lines.append(' '.join(current_line[:-1]))
                        current_line = [word]
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                for line in lines:
                    text_surface = self.font.render(line, True, 
                        THEME['user_text'] if self.is_user else THEME['assistant_text'])
                    surfaces.append(('text', text_surface))
                    y_offset += text_surface.get_height() + 5

        self.rendered_surfaces = surfaces
        self.height = y_offset

    def draw(self, surface, x, y):
        current_y = y
        bubble_color = THEME['user_bubble'] if self.is_user else THEME['assistant_bubble']
        
        for type_, text_surface in self.rendered_surfaces:
            if type_ == 'code':
                pygame.draw.rect(surface, THEME['code_bg'],
                    (x - 5, current_y - 5, text_surface.get_width() + 10, text_surface.get_height() + 10),
                    border_radius=5)
                surface.blit(text_surface, (x, current_y))
                current_y += text_surface.get_height() + 10
            else:
                text_rect = text_surface.get_rect()
                text_rect.topleft = (x, current_y)
                
                # Draw bubble background
                bubble_rect = text_rect.inflate(20, 10)
                if self.is_user:
                    bubble_rect.right = surface.get_width() - 20
                pygame.draw.rect(surface, bubble_color, bubble_rect, border_radius=10)
                
                # Draw text
                if self.is_user:
                    text_rect.right = surface.get_width() - 30
                surface.blit(text_surface, text_rect)
                current_y += text_rect.height + 5

class LoadingBubble:
    def __init__(self, width):
        self.width = width - 100
        self.height = 40
        self.dots_count = 0
        self.last_update = pygame.time.get_ticks()
        self.font = pygame.font.SysFont('Arial', 16)

    def render(self, surface, x, y):
        # Draw bubble background
        bubble_rect = pygame.Rect(x, y, 120, self.height)
        pygame.draw.rect(surface, THEME['loading_bubble'], bubble_rect, border_radius=10)
        
        # Draw loading dots
        current_time = pygame.time.get_ticks()
        if current_time - self.last_update >= LOADING_DOTS_INTERVAL:
            self.dots_count = (self.dots_count + 1) % (MAX_LOADING_DOTS + 1)
            self.last_update = current_time
        
        dots = "." * self.dots_count
        text_surface = self.font.render(f"Thinking{dots}", True, THEME['loading_color'])
        text_rect = text_surface.get_rect(center=bubble_rect.center)
        surface.blit(text_surface, text_rect)
        
        return self.height

class ModernChatUI:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Chat with Lamma2")
        
        self.input_box = ModernTextBox(
            PADDING,
            WINDOW_HEIGHT - INPUT_HEIGHT - PADDING,
            WINDOW_WIDTH - 2 * PADDING,
            INPUT_HEIGHT
        )
        
        self.messages = []
        self.scroll_offset = 0
        self.response_queue = Queue()
        self.stream_handler = StreamHandler(self.response_queue)
        
        print("DEBUG: Initializing LLM with model:", config['model']['name'])
        # Initialize OllamaLLM with proper streaming configuration
        self.llm = OllamaLLM(
            model=config['model']['name'],
            callbacks=[self.stream_handler],
            temperature=0.7,
            base_url="http://localhost:11434",
            system="You are a helpful AI assistant focused on providing clear, accurate, and detailed responses."
        )
        self.is_generating = False
        self.loading_bubble = LoadingBubble(WINDOW_WIDTH)
        self.current_response = ""

    def handle_llm_response(self):
        def run_llm(text):
            try:
                print(f"DEBUG: Starting LLM response for text: '{text}'")
                # Reset the stream handler's state
                self.stream_handler.current_response = ""
                self.stream_handler.is_complete = False
                
                print("DEBUG: Making LLM call...")
                try:
                    # Get the last user message
                    if not self.messages:
                        print("DEBUG: No messages found")
                        return
                        
                    user_text = text
                    print(f"DEBUG: Using user text: '{user_text}'")
                    
                    # Create a chat message
                    prompt = f"Human: {user_text}\nAssistant: "
                    print(f"DEBUG: Using prompt: '{prompt}'")
                    
                    # Make the LLM call with the formatted prompt
                    print("DEBUG: Calling LLM invoke...")
                    response = self.llm.invoke(user_text)
                    print(f"DEBUG: Raw LLM response received: '{response}'")
                    
                    # If streaming didn't work, send the complete response
                    if not self.stream_handler.is_complete and response:
                        print(f"DEBUG: Streaming didn't work, sending complete response: '{response}'")
                        self.response_queue.put(("complete", str(response)))
                    
                except Exception as llm_error:
                    print(f"DEBUG: LLM invocation error: {str(llm_error)}")
                    self.response_queue.put(("error", f"Error: {str(llm_error)}"))
                    raise llm_error
                    
            except Exception as e:
                print(f"DEBUG: Error in LLM call: {str(e)}")
                self.response_queue.put(("error", f"Error: {str(e)}"))
            finally:
                print("DEBUG: LLM call completed")
                self.is_generating = False

        # Get the last user message
        if not self.messages or not self.messages[-2].is_user:  # Check second to last message
            print("DEBUG: No valid user message found")
            return

        user_text = self.messages[-2].text  # Get the text from the last user message
        if not user_text:
            print("DEBUG: Empty user text")
            return

        print(f"DEBUG: Starting new thread for LLM response with text: '{user_text}'")
        self.is_generating = True
        thread = threading.Thread(target=run_llm, args=(user_text,))
        thread.daemon = True
        thread.start()
        print("DEBUG: Thread started")

    def run(self):
        clock = pygame.time.Clock()
        
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.input_box.active = self.input_box.rect.collidepoint(event.pos)
                
                if event.type == pygame.KEYDOWN and self.input_box.active:
                    if event.key == pygame.K_RETURN:
                        user_text = self.input_box.text.strip()
                        if user_text and not self.is_generating:  # Check for non-empty text
                            print(f"\nDEBUG: Processing user input: '{user_text}'")  # Added quotes to see whitespace
                            # Add user message
                            self.messages.append(MessageBubble(user_text, True, WINDOW_WIDTH))
                            
                            # Clear input and start generation
                            self.input_box.text = ""
                            self.current_response = ""
                            
                            # Add initial assistant message bubble
                            print("DEBUG: Adding initial assistant message bubble")
                            self.messages.append(MessageBubble("", False, WINDOW_WIDTH))
                            
                            # Start LLM response
                            self.handle_llm_response()
                            
                            # Auto-scroll to bottom
                            self.scroll_offset = max(0, self.get_total_height() - CHAT_AREA_HEIGHT)
                    
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_box.text = self.input_box.text[:-1]
                    else:
                        self.input_box.text += event.unicode

            # Check for new tokens
            try:
                while not self.response_queue.empty():
                    msg_type, content = self.response_queue.get_nowait()
                    print(f"DEBUG: Processing queue message: {msg_type}, content length: {len(content)}")
                    
                    if msg_type == "streaming":
                        # Update the last message (which should be the assistant's message)
                        if self.messages and not self.messages[-1].is_user:
                            print("DEBUG: Updating assistant message with new content")
                            self.messages[-1] = MessageBubble(content, False, WINDOW_WIDTH)
                            # Auto-scroll while receiving response
                            self.scroll_offset = max(0, self.get_total_height() - CHAT_AREA_HEIGHT)
                    
                    elif msg_type == "complete":
                        print("DEBUG: Completing message")
                        self.is_generating = False
                        # Update the final message
                        if self.messages and not self.messages[-1].is_user:
                            self.messages[-1] = MessageBubble(content, False, WINDOW_WIDTH)
                    
                    elif msg_type == "error":
                        print(f"DEBUG: Handling error message: {content}")
                        self.is_generating = False
                        # Replace the last message with the error message
                        if self.messages and not self.messages[-1].is_user:
                            self.messages[-1] = MessageBubble(content, False, WINDOW_WIDTH)
            
            except Exception as e:
                print(f"DEBUG: Error in message processing: {str(e)}")

            self.draw()
            clock.tick(60)

    def get_total_height(self):
        return sum(msg.height for msg in self.messages) + MESSAGE_SPACING * (len(self.messages) + 1)

    def draw(self):
        self.screen.fill(THEME['background'])
        
        # Draw messages
        y = PADDING - self.scroll_offset
        for message in self.messages:
            message.draw(self.screen, PADDING, y)
            y += message.height + MESSAGE_SPACING
        
        # Draw loading animation if generating
        if self.is_generating:
            loading_height = self.loading_bubble.render(self.screen, PADDING, y)
            y += loading_height + MESSAGE_SPACING
        
        # Draw input box
        self.input_box.draw(self.screen)
        
        pygame.display.flip()

if __name__ == "__main__":
    chat_ui = ModernChatUI()
    chat_ui.run() 