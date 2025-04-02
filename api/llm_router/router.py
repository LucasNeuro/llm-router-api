from typing import Dict, Any, Optional
from .deepseek import call_deepseek
from .gemini import call_gemini
from .mistral import call_mistral
from .gpt import call_gpt
from .classifier_agent import classify_prompt
from utils.logger import logger

# System prompts padrão para cada modelo
DEFAULT_SYSTEM_PROMPTS = {
    "gpt": """Você é um analista especializado em pensamento complexo e análise profunda.
                Forneça respostas detalhadas e bem estruturadas, considerando múltiplas perspectivas.
                Mantenha um tom profissional e acadêmico, com fundamentação sólida.
                Organize suas respostas em seções claras quando apropriado.
                Inclua análise de implicações práticas e teóricas quando relevante.""",

    "deepseek": """Você é um especialista técnico com profundo conhecimento em engenharia e tecnologia.
                Forneça explicações técnicas precisas e detalhadas.
                Use exemplos de código quando apropriado.
                Mantenha o foco em aspectos práticos e de implementação.
                Considere questões de performance, escalabilidade e boas práticas.""",

    "mistral": """Você é um comunicador criativo e claro.
                Forneça respostas concisas e diretas.
                Use linguagem acessível e exemplos práticos.
                Mantenha um tom conversacional e engajador.
                Foque em clareza e aplicabilidade.""",

    "gemini": """Você é um generalista versátil com conhecimento amplo.
                Forneça respostas balanceadas e práticas.
                Use exemplos do mundo real quando apropriado.
                Mantenha um tom informativo e acessível.
                Foque em soluções implementáveis."""
}

class LLMRouter:
    def __init__(self):
        # Available models and their functions
        self.models = {
            "deepseek": call_deepseek,
            "gemini": call_gemini,
            "mistral": call_mistral,
            "gpt": call_gpt
        }
        
        # Model capabilities for intelligent routing
        self.capabilities = {
            "deepseek": ["technical", "analysis", "documentation"],
            "gemini": ["code", "general", "multimodal"],
            "mistral": ["creative", "chat", "writing"],
            "gpt": ["complex", "reasoning", "expert"]
        }
    
    async def route(self, prompt: str, model: Optional[str] = None, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Routes the request to the most appropriate LLM
        """
        try:
            # If specific model requested, use it
            if model and model in self.models:
                logger.info(f"Using requested model: {model}")
                # Use provided system prompt or default for the model
                final_system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPTS[model]
                return await self.models[model](prompt, final_system_prompt)

            # Use intelligent classification
            logger.info(f"Classifying prompt: {prompt[:100]}...")
            classification = classify_prompt(prompt)
            
            if classification:
                recommended_model = classification["model"]
                task_type = classification["task_type"]
                confidence = classification["confidence"]
                metadata = classification["metadata"]
                
                logger.info(f"Classification results:")
                logger.info(f"- Recommended model: {recommended_model}")
                logger.info(f"- Task type: {task_type}")
                logger.info(f"- Confidence: {confidence:.2f}")
                logger.info(f"- Complexity: {metadata['complexity']}")
                logger.info(f"- Model scores: {metadata['model_scores']}")
                logger.info(f"- Indicators found:")
                logger.info(f"  * Complex: {metadata['complex_indicators_found']}")
                logger.info(f"  * Technical: {metadata['technical_indicators_found']}")
                logger.info(f"  * Creative: {metadata['creative_indicators_found']}")
                logger.info(f"  * Practical: {metadata['practical_indicators_found']}")
                
                if confidence >= 0.3:
                    try:
                        # Tenta usar o modelo recomendado
                        final_system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPTS[recommended_model]
                        logger.info(f"Attempting to use {recommended_model} with confidence {confidence:.2f}")
                        
                        response = await self.models[recommended_model](prompt, final_system_prompt)
                        if response.get("success", False):
                            response["classification"] = classification
                            logger.info(f"Successfully used {recommended_model}")
                            return response
                        else:
                            logger.warning(f"Model {recommended_model} failed to generate response")
                    except Exception as e:
                        logger.error(f"Error with recommended model {recommended_model}: {str(e)}")
                        
                    # Se o modelo recomendado falhar, tenta o segundo melhor
                    sorted_models = sorted(
                        metadata["model_scores"].items(),
                        key=lambda x: x[1],
                        reverse=True
                    )
                    
                    for model_name, score in sorted_models[1:]:
                        if score > 0:
                            try:
                                logger.info(f"Trying fallback model {model_name} with score {score}")
                                final_system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPTS[model_name]
                                response = await self.models[model_name](prompt, final_system_prompt)
                                if response.get("success", False):
                                    response["classification"] = classification
                                    logger.info(f"Successfully used fallback model {model_name}")
                                    return response
                            except Exception as e:
                                logger.error(f"Error with fallback model {model_name}: {str(e)}")
            
            # Fallback to GPT
            logger.info("Using GPT as final fallback")
            final_system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPTS["gpt"]
            return await self.models["gpt"](prompt, final_system_prompt)
        
        except Exception as e:
            error_msg = f"Routing error: {str(e)}"
            logger.error(error_msg)
            return {
                "text": error_msg,
                "model": "error",
                "success": False
            }