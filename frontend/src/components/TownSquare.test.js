import React from 'react'
import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import TownSquare from './TownSquare'

describe('TownSquare', () => {
  it('shows waiting message when no players', () => {
    render(<TownSquare players={[]} />)
    expect(screen.getByText('Waiting for players to join...')).toBeInTheDocument()
  })

  it('renders players and click events', () => {
    const mockClick = jest.fn()
    const players = [
      { id: 'p1', name: 'Alice', isAlive: true },
      { id: 'p2', name: 'Bob', isAlive: false }
    ]
    render(<TownSquare players={players} onPlayerClick={mockClick} />)
    fireEvent.click(screen.getByText('Alice'))
    expect(mockClick).toHaveBeenCalledWith('p1')
    fireEvent.click(screen.getByText('Bob'))
    expect(mockClick).toHaveBeenCalledTimes(1)
  })
}) 