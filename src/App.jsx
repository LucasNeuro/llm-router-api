import { useState } from 'react'
import {
  Box,
  Container,
  Flex,
  Heading,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  useColorMode,
  IconButton,
  HStack,
  Badge,
} from '@chakra-ui/react'
import { MoonIcon, SunIcon } from '@chakra-ui/icons'
import ChatInterface from './components/ChatInterface'
import RAGManager from './components/RAGManager'
import Settings from './components/Settings'

function App() {
  const { colorMode, toggleColorMode } = useColorMode()
  const [settings, setSettings] = useState({
    senderPhone: '',
    model: null,
    generateAudio: false,
    useRag: false,
    ragNamespace: null,
  })

  return (
    <Box minH="100vh">
      <Box
        bg={colorMode === 'dark' ? 'gray.800' : 'white'}
        borderBottom="1px"
        borderColor={colorMode === 'dark' ? 'gray.700' : 'gray.200'}
        py={4}
        position="sticky"
        top={0}
        zIndex={10}
        backdropFilter="blur(10px)"
      >
        <Container maxW="container.xl">
          <Flex justify="space-between" align="center">
            <HStack spacing={3}>
              <Heading size="lg" bgGradient="linear(to-r, brand.400, brand.600)" bgClip="text">
                MPC Chat
              </Heading>
              <Badge colorScheme="green" fontSize="xs">
                Roteamento Inteligente
              </Badge>
            </HStack>
            <IconButton
              icon={colorMode === 'dark' ? <SunIcon /> : <MoonIcon />}
              onClick={toggleColorMode}
              variant="ghost"
              aria-label="Alternar tema"
            />
          </Flex>
        </Container>
      </Box>

      <Container maxW="container.xl" py={6}>
        <Tabs colorScheme="brand" isLazy>
          <TabList>
            <Tab>Chat</Tab>
            <Tab>RAG</Tab>
            <Tab>Configurações</Tab>
          </TabList>

          <TabPanels>
            <TabPanel px={0}>
              <ChatInterface settings={settings} />
            </TabPanel>

            <TabPanel px={0}>
              <RAGManager />
            </TabPanel>

            <TabPanel px={0}>
              <Settings settings={settings} setSettings={setSettings} />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </Container>
    </Box>
  )
}

export default App
