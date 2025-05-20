import React from 'react'
import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import ChatPanel from './ChatPanel'

describe('ChatPanel', () => {
  const mockOnSend = jest.fn()
  const messages = [
    { sender: 'User1', text: 'Hello', timestamp: new Date().toISOString() },
    { sender: 'HumanPlayer1', text: 'Hi', timestamp: new Date().toISOString() }
  ]

  beforeEach(() => {
    mockOnSend.mockClear()
  })

  it('renders title', () => {
    render(<ChatPanel title="Test Chat" messages={[]} onSendMessage={mockOnSend} />)
    expect(screen.getByText('Test Chat')).toBeInTheDocument()
  })

  it('renders messages and identifies self', () => {
    render(<ChatPanel messages={messages} onSendMessage={mockOnSend} humanPlayerId="HumanPlayer1" />)
    expect(screen.getByText('User1: Hello')).toBeInTheDocument()
    expect(screen.getByText('You: Hi')).toBeInTheDocument()
  })

  it('calls onSendMessage on button click', () => {
    render(<ChatPanel messages={[]} onSendMessage={mockOnSend} humanPlayerId="HumanPlayer1" />)
    fireEvent.change(screen.getByPlaceholderText('Type your message...'), { target: { value: 'Test msg' } })
    fireEvent.click(screen.getByText('Send'))
    expect(mockOnSend).toHaveBeenCalledWith('Test msg')
  })

  it('calls onSendMessage on enter key', () => {
    render(<ChatPanel messages={[]} onSendMessage={mockOnSend} humanPlayerId="HumanPlayer1" />)
    const input = screen.getByPlaceholderText('Type your message...')
    fireEvent.change(input, { target: { value: 'Enter msg' } })
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 })
    expect(mockOnSend).toHaveBeenCalledWith('Enter msg')
  })

  it('hides input when readOnly', () => {
    render(<ChatPanel messages={[]} onSendMessage={mockOnSend} readOnly humanPlayerId="HumanPlayer1" />)
    expect(screen.queryByPlaceholderText('Type your message...')).toBeNull()
    expect(screen.queryByText('Send')).toBeNull()
  })
}) 