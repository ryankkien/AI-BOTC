import React from 'react'
import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import Controls from './Controls'

describe('Controls', () => {
  const humanId = 'human1'
  const players = [
    { id: 'human1', name: 'Human', isAlive: true },
    { id: 'p1', name: 'Player1', isAlive: true },
    { id: 'p2', name: 'Player2', isAlive: false }
  ]

  it('shows dead message when human is dead', () => {
    render(<Controls players={[{ id: 'human1', isAlive: false }]} humanPlayerId={humanId} gameState={{}} />)
    expect(screen.getByText('You are dead. No actions available.')).toBeInTheDocument()
  })

  it('handles nomination in day phase', () => {
    const mockNominate = jest.fn()
    render(<Controls players={players} humanPlayerId={humanId} gameState={{ currentPhase: 'DAY_CHAT' }} onNominate={mockNominate} />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'p1' } })
    fireEvent.click(screen.getByText('Nominate'))
    expect(mockNominate).toHaveBeenCalledWith('p1')
  })

  it('handles voting in voting phase', () => {
    const mockVote = jest.fn()
    render(<Controls players={players} humanPlayerId={humanId} gameState={{ currentPhase: 'VOTING', nominee: { id: 'p1', name: 'Player1' } }} onVote={mockVote} />)
    fireEvent.click(screen.getByText('Vote YES'))
    expect(mockVote).toHaveBeenCalledWith(true)
    fireEvent.click(screen.getByText('Vote NO'))
    expect(mockVote).toHaveBeenCalledWith(false)
  })

  it('handles night action in night phase', () => {
    const mockNight = jest.fn()
    render(<Controls players={players} humanPlayerId={humanId} gameState={{ currentPhase: 'NIGHT' }} onNightAction={mockNight} />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'p1' } })
    fireEvent.click(screen.getByText('Confirm Night Action'))
    expect(mockNight).toHaveBeenCalledWith({ target: 'p1' })
  })
}) 