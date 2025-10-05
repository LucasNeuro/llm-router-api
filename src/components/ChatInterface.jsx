import { useState, useRef, useEffect } from 'react'
import {
  Box,
  VStack,
  HStack,
  Input,
  Button,
  Text,
  Card,
  CardBody,
  Avatar,
  useToast,
  IconButton,
  Flex,
  Badge,
  Collapse,
  Divider,
  Spinner,
  useColorMode,
} from '@chakra-ui/react'
import {
  AttachmentIcon,
  InfoIcon,
  DeleteIcon,
  DownloadIcon,
} from '@chakra-ui/icons'
import { chatService } from '../services/api'

function ChatInterface({ settings }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [audioFile, setAudioFile] = useState(null)
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)
  const toast = useToast()
  const { colorMode } = useColorMode()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!input.trim() && !audioFile) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: input,
      timestamp: new Date().toLocaleTimeString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      let response

      if (audioFile) {
        response = await chatService.sendAudio(audioFile, {
          senderPhone: settings.senderPhone,
          generateAudio: settings.generateAudio,
        })
        setAudioFile(null)
      } else {
        response = await chatService.sendMessage(input, {
          senderPhone: settings.senderPhone,
          model: settings.model,
          generateAudio: settings.generateAudio,
          useRag: settings.useRag,
          ragNamespace: settings.ragNamespace,
        })
      }

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        text: response.text,
        model: response.model,
        confidence: response.confidence,
        costAnalysis: response.cost_analysis,
        audio: response.audio,
        transcription: response.transcription,
        timestamp: new Date().toLocaleTimeString(),
      }

      setMessages((prev) => [...prev, botMessage])
    } catch (error) {
      toast({
        title: 'Erro ao enviar mensagem',
        description: error.response?.data?.detail || error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleFileChange = (event) => {
    const file = event.target.files[0]
    if (file) {
      if (file.type.startsWith('audio/')) {
        setAudioFile(file)
        toast({
          title: 'Áudio selecionado',
          description: file.name,
          status: 'success',
          duration: 3000,
        })
      } else {
        toast({
          title: 'Arquivo inválido',
          description: 'Por favor, selecione um arquivo de áudio',
          status: 'error',
          duration: 3000,
        })
      }
    }
  }

  const handleClearMemory = async () => {
    if (!settings.senderPhone) {
      toast({
        title: 'Configure o telefone',
        description: 'Configure um número de telefone nas configurações',
        status: 'warning',
        duration: 3000,
      })
      return
    }

    try {
      await chatService.clearMemory(settings.senderPhone)
      setMessages([])
      toast({
        title: 'Memória limpa',
        status: 'success',
        duration: 3000,
      })
    } catch (error) {
      toast({
        title: 'Erro ao limpar memória',
        description: error.message,
        status: 'error',
        duration: 3000,
      })
    }
  }

  const downloadAudio = (audioData, messageId) => {
    if (!audioData?.base64) return

    const link = document.createElement('a')
    link.href = `data:audio/mpeg;base64,${audioData.base64}`
    link.download = `audio_${messageId}.mp3`
    link.click()
  }

  return (
    <VStack spacing={4} align="stretch" h="calc(100vh - 250px)">
      <Flex justify="space-between" align="center">
        <Text fontSize="sm" color="gray.500">
          {messages.length} mensagens
        </Text>
        <Button
          size="sm"
          leftIcon={<DeleteIcon />}
          onClick={handleClearMemory}
          colorScheme="red"
          variant="ghost"
        >
          Limpar histórico
        </Button>
      </Flex>

      <Box
        flex={1}
        overflowY="auto"
        bg={colorMode === 'dark' ? 'gray.800' : 'gray.50'}
        borderRadius="lg"
        p={4}
      >
        <VStack spacing={4} align="stretch">
          {messages.length === 0 && (
            <Card variant="outline">
              <CardBody>
                <VStack spacing={2}>
                  <InfoIcon boxSize={8} color="brand.500" />
                  <Text textAlign="center" color="gray.500">
                    Comece uma conversa enviando uma mensagem ou um áudio
                  </Text>
                </VStack>
              </CardBody>
            </Card>
          )}

          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onDownloadAudio={downloadAudio}
            />
          ))}

          {loading && (
            <HStack spacing={2} justify="center">
              <Spinner size="sm" color="brand.500" />
              <Text fontSize="sm" color="gray.500">
                Processando...
              </Text>
            </HStack>
          )}

          <div ref={messagesEndRef} />
        </VStack>
      </Box>

      <Card>
        <CardBody>
          <VStack spacing={3}>
            {audioFile && (
              <HStack
                w="100%"
                p={2}
                bg="brand.50"
                borderRadius="md"
                justify="space-between"
              >
                <Text fontSize="sm" color="brand.700">
                  {audioFile.name}
                </Text>
                <IconButton
                  size="sm"
                  icon={<DeleteIcon />}
                  onClick={() => setAudioFile(null)}
                  variant="ghost"
                  aria-label="Remover áudio"
                />
              </HStack>
            )}

            <HStack w="100%">
              <Input
                placeholder="Digite sua mensagem..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                disabled={loading}
              />
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="audio/*"
                style={{ display: 'none' }}
              />
              <IconButton
                icon={<AttachmentIcon />}
                onClick={() => fileInputRef.current?.click()}
                variant="ghost"
                aria-label="Anexar áudio"
              />
              <Button
                colorScheme="brand"
                onClick={handleSendMessage}
                isLoading={loading}
                loadingText="Enviando"
              >
                Enviar
              </Button>
            </HStack>
          </VStack>
        </CardBody>
      </Card>
    </VStack>
  )
}

function MessageBubble({ message, onDownloadAudio }) {
  const [showDetails, setShowDetails] = useState(false)
  const { colorMode } = useColorMode()
  const isUser = message.type === 'user'

  return (
    <Flex justify={isUser ? 'flex-end' : 'flex-start'}>
      <HStack
        spacing={3}
        maxW="80%"
        flexDirection={isUser ? 'row-reverse' : 'row'}
        align="flex-start"
      >
        <Avatar
          size="sm"
          name={isUser ? 'Você' : 'Bot'}
          bg={isUser ? 'brand.500' : 'green.500'}
        />

        <Card
          bg={
            isUser
              ? colorMode === 'dark'
                ? 'brand.700'
                : 'brand.500'
              : colorMode === 'dark'
              ? 'gray.700'
              : 'white'
          }
          color={isUser ? 'white' : undefined}
        >
          <CardBody>
            <VStack align="stretch" spacing={2}>
              {message.transcription && (
                <Box>
                  <Badge colorScheme="purple" mb={2}>
                    Transcrição
                  </Badge>
                  <Text fontSize="sm" fontStyle="italic">
                    "{message.transcription}"
                  </Text>
                  <Divider my={2} />
                </Box>
              )}

              <Text>{message.text}</Text>

              {!isUser && (
                <>
                  <HStack spacing={2} fontSize="xs" opacity={0.8}>
                    <Badge colorScheme="blue">{message.model}</Badge>
                    <Text>{message.timestamp}</Text>
                    {message.confidence && (
                      <Badge colorScheme="green">
                        {(message.confidence * 100).toFixed(0)}% confiança
                      </Badge>
                    )}
                  </HStack>

                  {message.audio && (
                    <Button
                      size="xs"
                      leftIcon={<DownloadIcon />}
                      onClick={() => onDownloadAudio(message.audio, message.id)}
                      variant="outline"
                    >
                      Download Áudio
                    </Button>
                  )}

                  {message.costAnalysis && (
                    <>
                      <Button
                        size="xs"
                        onClick={() => setShowDetails(!showDetails)}
                        variant="ghost"
                        leftIcon={<InfoIcon />}
                      >
                        {showDetails ? 'Ocultar' : 'Ver'} custos
                      </Button>

                      <Collapse in={showDetails}>
                        <Box
                          p={2}
                          bg={colorMode === 'dark' ? 'gray.800' : 'gray.100'}
                          borderRadius="md"
                          fontSize="xs"
                        >
                          <VStack align="stretch" spacing={1}>
                            <HStack justify="space-between">
                              <Text fontWeight="bold">Tokens:</Text>
                              <Text>
                                {message.costAnalysis.tokens.input_tokens} in /{' '}
                                {message.costAnalysis.tokens.output_tokens} out
                              </Text>
                            </HStack>
                            <HStack justify="space-between">
                              <Text fontWeight="bold">Custo USD:</Text>
                              <Text>{message.costAnalysis.costs.usd.formatted}</Text>
                            </HStack>
                            <HStack justify="space-between">
                              <Text fontWeight="bold">Custo BRL:</Text>
                              <Text>{message.costAnalysis.costs.brl.formatted}</Text>
                            </HStack>
                          </VStack>
                        </Box>
                      </Collapse>
                    </>
                  )}
                </>
              )}
            </VStack>
          </CardBody>
        </Card>
      </HStack>
    </Flex>
  )
}

export default ChatInterface
