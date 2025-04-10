from typing import Dict, Any, Optional, List
import json
from loguru import logger
from ..models.agent import Agent, g4_agent
from ..llm_router.router import LLMRouter
from .conversation_memory import conversation_manager

class AgentService:
    """Serviço para gerenciar a interação de agentes com LLMs"""
    
    def __init__(self):
        self.llm_router = LLMRouter()
        self.agents: Dict[str, Agent] = {
            "g4-telecom": g4_agent
        }
        
    def register_agent(self, agent: Agent) -> None:
        """Registra um novo agente no serviço"""
        self.agents[agent.id] = agent
        logger.info(f"Agente '{agent.id}' registrado com sucesso")
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Recupera um agente pelo ID"""
        return self.agents.get(agent_id)
    
    def _format_agent_prompt(self, agent: Agent, message: str, context: str = "") -> str:
        """Formata o prompt do agente com o contexto e a mensagem atual"""
        
        # Formata as informações da empresa para o prompt
        company_info_str = "\n".join([
            f"- {key.replace('_', ' ').title()}: {value}" 
            for key, value in agent.knowledge.company_info.items()
        ])
        
        # Formata os traços de personalidade
        traits_str = ", ".join(agent.personality.traits)
        
        # Substitui as variáveis no template
        prompt = agent.prompt_template.format(
            name=agent.config.name,
            tone=agent.personality.tone,
            traits=traits_str,
            language_style=agent.personality.language_style,
            formality_level=agent.personality.formality_level,
            company_info=company_info_str,
            message=message,
            context=context
        )
        
        return prompt
    
    async def _should_handoff_to_human(self, agent: Agent, message: str) -> bool:
        """Verifica se a mensagem deve ser encaminhada para um humano"""
        message_lower = message.lower()
        
        # Verifica se algum gatilho de transferência está presente na mensagem
        for trigger in agent.config.human_handoff_triggers:
            if trigger.lower() in message_lower:
                logger.info(f"Gatilho de transferência detectado: '{trigger}'")
                return True
                
        return False
    
    async def _get_product_info(self, agent: Agent, product_name: str) -> Optional[Dict[str, Any]]:
        """Recupera informações sobre um produto específico"""
        product_name_lower = product_name.lower()
        
        for product in agent.knowledge.products:
            if product["nome"].lower() in product_name_lower:
                return product
                
        return None
    
    async def _get_plan_info(self, agent: Agent, plan_query: str) -> List[Dict[str, Any]]:
        """Recupera informações sobre planos com base na consulta"""
        matching_plans = []
        plan_query_lower = plan_query.lower()
        
        # Busca em todas as categorias de planos
        for category, plans in agent.knowledge.plans.items():
            for plan in plans:
                # Verifica se o nome do plano ou velocidade estão na consulta
                if (plan["nome"].lower() in plan_query_lower or 
                    plan["velocidade"].lower() in plan_query_lower):
                    matching_plan = plan.copy()
                    matching_plan["categoria"] = category
                    matching_plans.append(matching_plan)
                    
        return matching_plans
    
    async def process_message(
        self, 
        agent_id: str, 
        message: str, 
        sender_phone: str
    ) -> Dict[str, Any]:
        """Processa uma mensagem usando o agente especificado"""
        try:
            # Recupera o agente
            agent = self.get_agent(agent_id)
            if not agent:
                logger.error(f"Agente com ID '{agent_id}' não encontrado")
                return {
                    "text": "Desculpe, houve um erro no processamento da sua mensagem. Por favor, tente novamente mais tarde.",
                    "success": False,
                    "need_human": True
                }
            
            # Verifica se deve transferir para humano
            need_human = await self._should_handoff_to_human(agent, message)
            if need_human:
                return {
                    "text": f"Olá! Entendo que você precisa de um atendimento mais personalizado. Vou transferir você para um dos nossos atendentes humanos da G4 TELECOM. Aguarde um momento, por favor.",
                    "success": True,
                    "need_human": True
                }
            
            # Recupera o contexto da conversa
            context = await conversation_manager.format_conversation_for_llm(sender_phone)
            
            # Formata o prompt do agente
            prompt = self._format_agent_prompt(agent, message, context)
            
            # Envia o prompt para o LLM Router
            result = await self.llm_router.route_prompt(
                prompt=prompt,
                sender_phone=sender_phone
            )
            
            # Adiciona metadados do agente à resposta
            result["agent_id"] = agent_id
            result["agent_name"] = agent.config.name
            result["need_human"] = False
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem com agente: {str(e)}")
            logger.exception("Stacktrace completo:")
            
            return {
                "text": "Desculpe, ocorreu um erro ao processar sua mensagem. Estou encaminhando para um atendente humano da G4 TELECOM que poderá ajudá-lo melhor.",
                "success": False,
                "need_human": True
            }

# Instância global do serviço de agentes
agent_service = AgentService() 