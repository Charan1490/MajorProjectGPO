import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  IconButton,
  Paper,
  TextField,
  Typography,
  Avatar,
  Fade,
  CircularProgress,
  Tooltip,
  Chip,
  Divider
} from '@mui/material';
import {
  Chat as ChatIcon,
  Close as CloseIcon,
  Send as SendIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
  DeleteSweep as ClearIcon,
  Minimize as MinimizeIcon
} from '@mui/icons-material';
import './ChatbotWidget.css';

const ChatbotWidget = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m your GPO & CIS Benchmark assistant. Ask me anything about Group Policy Objects, CIS benchmarks, or Windows security configurations.',
      timestamp: new Date().toISOString()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  const API_URL = process.env.REACT_APP_GPO_CHATBOT_API_URL;
  const API_KEY = process.env.REACT_APP_GPO_CHATBOT_API_KEY;

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const toggleChat = () => {
    setIsOpen(!isOpen);
    setIsMinimized(false);
    setError(null);
  };

  const minimizeChat = () => {
    setIsMinimized(!isMinimized);
  };

  const clearChat = () => {
    setMessages([
      {
        role: 'assistant',
        content: 'Chat history cleared. How can I help you today?',
        timestamp: new Date().toISOString()
      }
    ]);
    setError(null);
  };

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY
        },
        body: JSON.stringify({
          message: inputMessage,
          max_length: 300,
          temperature: 0.7
        })
      });

      const data = await response.json();

      if (data.success && data.data) {
        const botMessage = {
          role: 'assistant',
          content: data.data.answer,
          model: data.data.model,
          cached: data.data.cached,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, botMessage]);
      } else {
        throw new Error(data.error?.message || 'Failed to get response');
      }
    } catch (err) {
      console.error('Chatbot error:', err);
      setError(err.message || 'Failed to connect to chatbot. Please try again.');
      
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again or contact support if the issue persists.',
        isError: true,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const quickQuestions = [
    'What is CIS Benchmark?',
    'How to configure password policies?',
    'Explain user rights assignment',
    'Top 10 GPO security settings'
  ];

  const handleQuickQuestion = (question) => {
    setInputMessage(question);
  };

  return (
    <>
      {/* Floating Chat Button */}
      {!isOpen && (
        <Tooltip title="Ask GPO Assistant" placement="left">
          <Box className="chatbot-float-button" onClick={toggleChat}>
            <ChatIcon sx={{ fontSize: 32, color: 'white' }} />
            <Box className="chatbot-pulse" />
          </Box>
        </Tooltip>
      )}

      {/* Chat Window */}
      <Fade in={isOpen}>
        <Paper 
          className={`chatbot-window ${isMinimized ? 'minimized' : ''}`}
          elevation={8}
        >
          {/* Chat Header */}
          <Box className="chatbot-header">
            <Box display="flex" alignItems="center" gap={1.5}>
              <Avatar 
                sx={{ 
                  bgcolor: 'white', 
                  width: 40, 
                  height: 40,
                  border: '2px solid rgba(255,255,255,0.3)'
                }}
              >
                <BotIcon sx={{ color: '#667eea', fontSize: 24 }} />
              </Avatar>
              <Box>
                <Typography variant="h6" sx={{ color: 'white', fontWeight: 600, fontSize: '1.1rem' }}>
                  GPO Assistant
                </Typography>
                <Box display="flex" alignItems="center" gap={0.5}>
                  <Box 
                    sx={{ 
                      width: 8, 
                      height: 8, 
                      borderRadius: '50%', 
                      bgcolor: '#4ade80',
                      boxShadow: '0 0 8px #4ade80'
                    }} 
                  />
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
                    Online
                  </Typography>
                </Box>
              </Box>
            </Box>
            <Box display="flex" gap={0.5}>
              <Tooltip title="Clear Chat">
                <IconButton size="small" onClick={clearChat} sx={{ color: 'white' }}>
                  <ClearIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title={isMinimized ? "Expand" : "Minimize"}>
                <IconButton size="small" onClick={minimizeChat} sx={{ color: 'white' }}>
                  <MinimizeIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="Close">
                <IconButton size="small" onClick={toggleChat} sx={{ color: 'white' }}>
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {/* Chat Body */}
          {!isMinimized && (
            <>
              <Box className="chatbot-messages" ref={chatContainerRef}>
                {messages.map((message, index) => (
                  <Box
                    key={index}
                    className={`message-wrapper ${message.role}`}
                  >
                    <Box className={`message-bubble ${message.role} ${message.isError ? 'error' : ''}`}>
                      <Box display="flex" alignItems="flex-start" gap={1}>
                        {message.role === 'assistant' && (
                          <Avatar sx={{ width: 28, height: 28, bgcolor: '#667eea' }}>
                            <BotIcon sx={{ fontSize: 18 }} />
                          </Avatar>
                        )}
                        <Box flex={1}>
                          <Typography 
                            variant="body2" 
                            sx={{ 
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                              lineHeight: 1.6
                            }}
                          >
                            {message.content}
                          </Typography>
                          <Box display="flex" alignItems="center" gap={1} mt={0.5}>
                            <Typography 
                              variant="caption" 
                              sx={{ 
                                opacity: 0.7,
                                fontSize: '0.7rem'
                              }}
                            >
                              {formatTime(message.timestamp)}
                            </Typography>
                            {message.model && (
                              <Chip 
                                label={message.model} 
                                size="small" 
                                sx={{ 
                                  height: 16, 
                                  fontSize: '0.65rem',
                                  opacity: 0.7
                                }} 
                              />
                            )}
                            {message.cached && (
                              <Chip 
                                label="cached" 
                                size="small" 
                                color="success"
                                sx={{ 
                                  height: 16, 
                                  fontSize: '0.65rem',
                                  opacity: 0.7
                                }} 
                              />
                            )}
                          </Box>
                        </Box>
                        {message.role === 'user' && (
                          <Avatar sx={{ width: 28, height: 28, bgcolor: '#3b82f6' }}>
                            <PersonIcon sx={{ fontSize: 18 }} />
                          </Avatar>
                        )}
                      </Box>
                    </Box>
                  </Box>
                ))}

                {isLoading && (
                  <Box className="message-wrapper assistant">
                    <Box className="message-bubble assistant typing">
                      <Box display="flex" alignItems="center" gap={1}>
                        <Avatar sx={{ width: 28, height: 28, bgcolor: '#667eea' }}>
                          <BotIcon sx={{ fontSize: 18 }} />
                        </Avatar>
                        <Box className="typing-indicator">
                          <span></span>
                          <span></span>
                          <span></span>
                        </Box>
                      </Box>
                    </Box>
                  </Box>
                )}

                {error && (
                  <Box className="chatbot-error">
                    <Typography variant="caption" color="error">
                      ⚠️ {error}
                    </Typography>
                  </Box>
                )}

                <div ref={messagesEndRef} />
              </Box>

              {/* Quick Questions */}
              {messages.length <= 1 && (
                <Box className="quick-questions">
                  <Typography variant="caption" sx={{ mb: 1, display: 'block', opacity: 0.7 }}>
                    Quick questions:
                  </Typography>
                  <Box display="flex" flexWrap="wrap" gap={0.5}>
                    {quickQuestions.map((question, idx) => (
                      <Chip
                        key={idx}
                        label={question}
                        size="small"
                        onClick={() => handleQuickQuestion(question)}
                        sx={{ 
                          cursor: 'pointer',
                          fontSize: '0.75rem',
                          '&:hover': {
                            bgcolor: 'primary.main',
                            color: 'white'
                          }
                        }}
                      />
                    ))}
                  </Box>
                  <Divider sx={{ mt: 1.5 }} />
                </Box>
              )}

              {/* Chat Input */}
              <Box className="chatbot-input">
                <TextField
                  fullWidth
                  multiline
                  maxRows={3}
                  placeholder="Ask about GPO, CIS Benchmark, or Windows security..."
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={isLoading}
                  variant="outlined"
                  size="small"
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 3,
                      bgcolor: 'background.paper'
                    }
                  }}
                  InputProps={{
                    endAdornment: (
                      <IconButton
                        onClick={sendMessage}
                        disabled={isLoading || !inputMessage.trim()}
                        sx={{
                          bgcolor: 'primary.main',
                          color: 'white',
                          '&:hover': {
                            bgcolor: 'primary.dark'
                          },
                          '&.Mui-disabled': {
                            bgcolor: 'action.disabledBackground'
                          }
                        }}
                        size="small"
                      >
                        {isLoading ? (
                          <CircularProgress size={20} sx={{ color: 'white' }} />
                        ) : (
                          <SendIcon fontSize="small" />
                        )}
                      </IconButton>
                    )
                  }}
                />
              </Box>

              {/* Footer */}
              <Box className="chatbot-footer">
                <Typography variant="caption" sx={{ opacity: 0.6 }}>
                  Powered by HuggingFace AI
                </Typography>
              </Box>
            </>
          )}
        </Paper>
      </Fade>
    </>
  );
};

export default ChatbotWidget;
