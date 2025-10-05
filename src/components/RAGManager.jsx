import { useState } from 'react'
import {
  Box,
  VStack,
  HStack,
  Input,
  Button,
  Textarea,
  Text,
  Card,
  CardBody,
  CardHeader,
  Heading,
  useToast,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  FormControl,
  FormLabel,
  NumberInput,
  NumberInputField,
  Badge,
  Divider,
  Code,
  useColorMode,
} from '@chakra-ui/react'
import { SearchIcon, AddIcon } from '@chakra-ui/icons'
import { ragService } from '../services/api'

function RAGManager() {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [topK, setTopK] = useState(5)
  const [namespace, setNamespace] = useState('')

  const [documents, setDocuments] = useState([{ id: '', content: '', metadata: {} }])
  const [indexLoading, setIndexLoading] = useState(false)

  const toast = useToast()
  const { colorMode } = useColorMode()

  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    setSearchLoading(true)
    try {
      const response = await ragService.search(
        searchQuery,
        topK,
        namespace || null
      )
      setSearchResults(response.results || [])
      toast({
        title: 'Busca concluída',
        description: `${response.results?.length || 0} resultados encontrados`,
        status: 'success',
        duration: 3000,
      })
    } catch (error) {
      toast({
        title: 'Erro na busca',
        description: error.response?.data?.detail || error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      })
    } finally {
      setSearchLoading(false)
    }
  }

  const handleAddDocument = () => {
    setDocuments([...documents, { id: '', content: '', metadata: {} }])
  }

  const handleRemoveDocument = (index) => {
    setDocuments(documents.filter((_, i) => i !== index))
  }

  const handleDocumentChange = (index, field, value) => {
    const updated = [...documents]
    updated[index][field] = value
    setDocuments(updated)
  }

  const handleIndexDocuments = async () => {
    const validDocs = documents.filter((doc) => doc.content.trim())

    if (validDocs.length === 0) {
      toast({
        title: 'Nenhum documento válido',
        description: 'Adicione pelo menos um documento com conteúdo',
        status: 'warning',
        duration: 3000,
      })
      return
    }

    setIndexLoading(true)
    try {
      const docsToIndex = validDocs.map((doc) => ({
        id: doc.id || undefined,
        content: doc.content,
        metadata: doc.metadata || {},
        namespace: namespace || undefined,
      }))

      const response = await ragService.indexDocuments(docsToIndex, namespace || null)

      toast({
        title: 'Documentos indexados',
        description: `${response.indexed} documentos indexados com sucesso`,
        status: 'success',
        duration: 3000,
      })

      setDocuments([{ id: '', content: '', metadata: {} }])
    } catch (error) {
      toast({
        title: 'Erro ao indexar',
        description: error.response?.data?.detail || error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      })
    } finally {
      setIndexLoading(false)
    }
  }

  return (
    <VStack spacing={6} align="stretch">
      <Card>
        <CardHeader>
          <Heading size="md">RAG - Retrieval Augmented Generation</Heading>
          <Text fontSize="sm" color="gray.500" mt={2}>
            Indexe documentos e busque informações relevantes para melhorar as respostas
          </Text>
        </CardHeader>
      </Card>

      <Tabs colorScheme="brand" isLazy>
        <TabList>
          <Tab>Buscar</Tab>
          <Tab>Indexar</Tab>
        </TabList>

        <TabPanels>
          <TabPanel px={0}>
            <VStack spacing={4} align="stretch">
              <Card>
                <CardBody>
                  <VStack spacing={4}>
                    <FormControl>
                      <FormLabel>Namespace (opcional)</FormLabel>
                      <Input
                        placeholder="Ex: documentacao, base-conhecimento"
                        value={namespace}
                        onChange={(e) => setNamespace(e.target.value)}
                      />
                    </FormControl>

                    <FormControl>
                      <FormLabel>Query de busca</FormLabel>
                      <Input
                        placeholder="Digite sua busca..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                      />
                    </FormControl>

                    <FormControl>
                      <FormLabel>Número de resultados (top_k)</FormLabel>
                      <NumberInput
                        value={topK}
                        onChange={(_, val) => setTopK(val)}
                        min={1}
                        max={20}
                      >
                        <NumberInputField />
                      </NumberInput>
                    </FormControl>

                    <Button
                      leftIcon={<SearchIcon />}
                      colorScheme="brand"
                      onClick={handleSearch}
                      isLoading={searchLoading}
                      loadingText="Buscando"
                      w="100%"
                    >
                      Buscar
                    </Button>
                  </VStack>
                </CardBody>
              </Card>

              {searchResults.length > 0 && (
                <VStack spacing={3} align="stretch">
                  <Text fontWeight="bold">
                    Resultados ({searchResults.length})
                  </Text>

                  {searchResults.map((result, index) => (
                    <Card
                      key={index}
                      bg={colorMode === 'dark' ? 'gray.800' : 'white'}
                    >
                      <CardBody>
                        <VStack align="stretch" spacing={2}>
                          <HStack justify="space-between">
                            <Badge colorScheme="brand">
                              Relevância: {(result.similarity * 100).toFixed(1)}%
                            </Badge>
                            {result.namespace && (
                              <Badge>{result.namespace}</Badge>
                            )}
                          </HStack>

                          <Text>{result.content}</Text>

                          {result.metadata && Object.keys(result.metadata).length > 0 && (
                            <>
                              <Divider />
                              <Box>
                                <Text fontSize="sm" fontWeight="bold" mb={1}>
                                  Metadata:
                                </Text>
                                <Code
                                  p={2}
                                  borderRadius="md"
                                  w="100%"
                                  display="block"
                                  fontSize="xs"
                                >
                                  {JSON.stringify(result.metadata, null, 2)}
                                </Code>
                              </Box>
                            </>
                          )}
                        </VStack>
                      </CardBody>
                    </Card>
                  ))}
                </VStack>
              )}
            </VStack>
          </TabPanel>

          <TabPanel px={0}>
            <VStack spacing={4} align="stretch">
              <Card>
                <CardBody>
                  <VStack spacing={4}>
                    <FormControl>
                      <FormLabel>Namespace (opcional)</FormLabel>
                      <Input
                        placeholder="Ex: documentacao, base-conhecimento"
                        value={namespace}
                        onChange={(e) => setNamespace(e.target.value)}
                      />
                      <Text fontSize="xs" color="gray.500" mt={1}>
                        Use namespaces para organizar seus documentos
                      </Text>
                    </FormControl>
                  </VStack>
                </CardBody>
              </Card>

              {documents.map((doc, index) => (
                <Card key={index}>
                  <CardBody>
                    <VStack spacing={3}>
                      <HStack w="100%" justify="space-between">
                        <Text fontWeight="bold">Documento {index + 1}</Text>
                        {documents.length > 1 && (
                          <Button
                            size="sm"
                            colorScheme="red"
                            variant="ghost"
                            onClick={() => handleRemoveDocument(index)}
                          >
                            Remover
                          </Button>
                        )}
                      </HStack>

                      <FormControl>
                        <FormLabel fontSize="sm">ID (opcional)</FormLabel>
                        <Input
                          placeholder="ID único do documento"
                          value={doc.id}
                          onChange={(e) =>
                            handleDocumentChange(index, 'id', e.target.value)
                          }
                          size="sm"
                        />
                      </FormControl>

                      <FormControl>
                        <FormLabel fontSize="sm">Conteúdo *</FormLabel>
                        <Textarea
                          placeholder="Digite o conteúdo do documento..."
                          value={doc.content}
                          onChange={(e) =>
                            handleDocumentChange(index, 'content', e.target.value)
                          }
                          rows={4}
                        />
                      </FormControl>

                      <FormControl>
                        <FormLabel fontSize="sm">Metadata (JSON opcional)</FormLabel>
                        <Textarea
                          placeholder='{"categoria": "exemplo", "autor": "nome"}'
                          value={JSON.stringify(doc.metadata)}
                          onChange={(e) => {
                            try {
                              const parsed = JSON.parse(e.target.value || '{}')
                              handleDocumentChange(index, 'metadata', parsed)
                            } catch (err) {
                              // Invalid JSON, ignore
                            }
                          }}
                          rows={2}
                          fontFamily="mono"
                          fontSize="xs"
                        />
                      </FormControl>
                    </VStack>
                  </CardBody>
                </Card>
              ))}

              <HStack spacing={3}>
                <Button
                  leftIcon={<AddIcon />}
                  onClick={handleAddDocument}
                  variant="outline"
                  flex={1}
                >
                  Adicionar documento
                </Button>

                <Button
                  colorScheme="brand"
                  onClick={handleIndexDocuments}
                  isLoading={indexLoading}
                  loadingText="Indexando"
                  flex={1}
                >
                  Indexar documentos
                </Button>
              </HStack>
            </VStack>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </VStack>
  )
}

export default RAGManager
