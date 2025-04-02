from loguru import logger
from rich.console import Console
from rich.traceback import install as install_rich_traceback
from rich.logging import RichHandler
import sys
import json
from datetime import datetime
from pathlib import Path

# Instala o rich traceback handler
install_rich_traceback(show_locals=True)

# Cria console do Rich
console = Console()

# Configura diretório de logs
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Remove handlers padrão
logger.remove()

# Adiciona handler para o console com formatação rica
logger.add(
    RichHandler(
        console=console,
        show_path=False,
        enable_link_path=True,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
    ),
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

# Adiciona handler para arquivo de log
logger.add(
    log_dir / "api_{time}.log",
    rotation="500 MB",
    retention="10 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    encoding="utf-8"
)

def log_api_request(request_data: dict, route: str):
    """Log formatado para requisições API"""
    logger.info(f"[bold blue]API Request[/bold blue] to [bold green]{route}[/bold green]")
    console.print("[bold]Request Data:[/bold]", style="yellow")
    console.print_json(json.dumps(request_data))

def log_api_response(response_data: dict, route: str, success: bool = True):
    """Log formatado para respostas API"""
    status = "[bold green]Success[/bold green]" if success else "[bold red]Error[/bold red]"
    logger.info(f"[bold blue]API Response[/bold blue] from [bold green]{route}[/bold green] - Status: {status}")
    console.print("[bold]Response Data:[/bold]", style="yellow")
    console.print_json(json.dumps(response_data))

def log_llm_call(model: str, prompt: str):
    """Log formatado para chamadas LLM"""
    logger.info(f"[bold purple]LLM Call[/bold purple] to [bold blue]{model}[/bold blue]")
    console.print("[bold]Prompt:[/bold]", style="cyan")
    console.print(prompt, style="bright_black")

def log_llm_response(model: str, response: str, success: bool = True):
    """Log formatado para respostas LLM"""
    status = "[bold green]Success[/bold green]" if success else "[bold red]Error[/bold red]"
    logger.info(f"[bold purple]LLM Response[/bold purple] from [bold blue]{model}[/bold blue] - Status: {status}")
    console.print("[bold]Response:[/bold]", style="cyan")
    console.print(response, style="bright_black")

def log_error(error: Exception, context: str = None):
    """Log formatado para erros"""
    logger.error(f"[bold red]Error[/bold red] {f'in {context} ' if context else ''}- {str(error)}")
    console.print_exception(show_locals=True)

# Exemplo de uso:
if __name__ == "__main__":
    # Teste dos logs
    logger.info("Teste de log info")
    logger.warning("Teste de log warning")
    logger.error("Teste de log error")
    
    test_request = {"message": "test", "model": "test-model"}
    log_api_request(test_request, "/chat")
    
    test_response = {"text": "test response", "success": True}
    log_api_response(test_response, "/chat")
    
    try:
        raise ValueError("Teste de erro")
    except Exception as e:
        log_error(e, "teste") 