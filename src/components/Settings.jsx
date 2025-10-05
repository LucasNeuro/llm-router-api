import {
  VStack,
  FormControl,
  FormLabel,
  Input,
  Switch,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Text,
  Select,
  Divider,
  HStack,
  Badge,
  useColorMode,
} from '@chakra-ui/react'

const AVAILABLE_MODELS = [
  { value: '', label: 'Automático (recomendado)' },
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'claude-3-5-sonnet', label: 'Claude 3.5 Sonnet' },
  { value: 'claude-3-5-haiku', label: 'Claude 3.5 Haiku' },
  { value: 'gemini-2.0-flash-exp', label: 'Gemini 2.0 Flash' },
  { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
  { value: 'deepseek-chat', label: 'DeepSeek Chat' },
  { value: 'mistral-large', label: 'Mistral Large' },
]

function Settings({ settings, setSettings }) {
  const { colorMode } = useColorMode()

  const handleChange = (field, value) => {
    setSettings((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  return (
    <VStack spacing={6} align="stretch">
      <Card>
        <CardHeader>
          <Heading size="md">Configurações</Heading>
          <Text fontSize="sm" color="gray.500" mt={2}>
            Personalize o comportamento do chat e das requisições
          </Text>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader pb={2}>
          <Heading size="sm">Identificação</Heading>
        </CardHeader>
        <CardBody>
          <VStack spacing={4}>
            <FormControl>
              <FormLabel>
                Número de telefone
                <Badge ml={2} colorScheme="blue" fontSize="xs">
                  Opcional
                </Badge>
              </FormLabel>
              <Input
                placeholder="+55 11 99999-9999"
                value={settings.senderPhone}
                onChange={(e) => handleChange('senderPhone', e.target.value)}
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                Use para manter contexto de conversas entre sessões
              </Text>
            </FormControl>
          </VStack>
        </CardBody>
      </Card>

      <Card>
        <CardHeader pb={2}>
          <Heading size="sm">Modelo de IA</Heading>
        </CardHeader>
        <CardBody>
          <VStack spacing={4}>
            <FormControl>
              <FormLabel>Modelo preferido</FormLabel>
              <Select
                value={settings.model || ''}
                onChange={(e) => handleChange('model', e.target.value || null)}
              >
                {AVAILABLE_MODELS.map((model) => (
                  <option key={model.value} value={model.value}>
                    {model.label}
                  </option>
                ))}
              </Select>
              <Text fontSize="xs" color="gray.500" mt={1}>
                Deixe em "Automático" para o sistema escolher o melhor modelo baseado na sua
                pergunta
              </Text>
            </FormControl>
          </VStack>
        </CardBody>
      </Card>

      <Card>
        <CardHeader pb={2}>
          <Heading size="sm">Recursos Avançados</Heading>
        </CardHeader>
        <CardBody>
          <VStack spacing={4} align="stretch">
            <FormControl display="flex" alignItems="center">
              <FormLabel htmlFor="generate-audio" mb="0" flex={1}>
                <VStack align="start" spacing={0}>
                  <Text>Gerar áudio das respostas</Text>
                  <Text fontSize="xs" color="gray.500">
                    Converte as respostas do bot em áudio
                  </Text>
                </VStack>
              </FormLabel>
              <Switch
                id="generate-audio"
                colorScheme="brand"
                isChecked={settings.generateAudio}
                onChange={(e) => handleChange('generateAudio', e.target.checked)}
              />
            </FormControl>

            <Divider />

            <FormControl display="flex" alignItems="center">
              <FormLabel htmlFor="use-rag" mb="0" flex={1}>
                <VStack align="start" spacing={0}>
                  <HStack>
                    <Text>Usar RAG</Text>
                    <Badge colorScheme="purple" fontSize="xs">
                      Experimental
                    </Badge>
                  </HStack>
                  <Text fontSize="xs" color="gray.500">
                    Busca contexto em documentos indexados
                  </Text>
                </VStack>
              </FormLabel>
              <Switch
                id="use-rag"
                colorScheme="brand"
                isChecked={settings.useRag}
                onChange={(e) => handleChange('useRag', e.target.checked)}
              />
            </FormControl>

            {settings.useRag && (
              <FormControl>
                <FormLabel fontSize="sm">Namespace RAG</FormLabel>
                <Input
                  placeholder="Ex: documentacao"
                  value={settings.ragNamespace || ''}
                  onChange={(e) => handleChange('ragNamespace', e.target.value || null)}
                  size="sm"
                />
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Filtra busca por namespace específico
                </Text>
              </FormControl>
            )}
          </VStack>
        </CardBody>
      </Card>

      <Card bg={colorMode === 'dark' ? 'blue.900' : 'blue.50'} borderColor="blue.200">
        <CardBody>
          <VStack align="start" spacing={2}>
            <Heading size="xs" color={colorMode === 'dark' ? 'blue.200' : 'blue.700'}>
              Sobre o Roteamento Inteligente
            </Heading>
            <Text fontSize="sm" color={colorMode === 'dark' ? 'blue.100' : 'blue.600'}>
              O sistema analisa automaticamente suas perguntas e escolhe o melhor modelo de IA
              para responder, otimizando custos e qualidade. Cada modelo tem características
              específicas: GPT-4 para análises complexas, Claude para textos longos, Gemini para
              velocidade, DeepSeek para custo-benefício.
            </Text>
          </VStack>
        </CardBody>
      </Card>
    </VStack>
  )
}

export default Settings
