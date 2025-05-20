import React from 'react'
import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import LLMDebugPanel from './LLMDebugPanel'

describe('LLMDebugPanel', () => {
  it('shows none when empty', () => {
    const onClose = jest.fn()
    render(<LLMDebugPanel title="Debug" debugData={{}} onClose={onClose} />)
    expect(screen.getAllByText('none').length).toBe(2)
  })

  it('shows prompts and responses', () => {
    const onClose = jest.fn()
    const debugData = { prompts: ['p1'], responses: ['r1'] }
    render(<LLMDebugPanel title="Debug" debugData={debugData} onClose={onClose} />)
    expect(screen.getByText('p1')).toBeInTheDocument()
    expect(screen.getByText('r1')).toBeInTheDocument()
  })

  it('calls onClose on click', () => {
    const onClose = jest.fn()
    render(<LLMDebugPanel title="Debug" debugData={{}} onClose={onClose} />)
    fireEvent.click(screen.getByText('x'))
    expect(onClose).toHaveBeenCalled()
  })
}) 