import React from 'react'
import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import PrivateInfoPanel from './PrivateInfoPanel'

describe('PrivateInfoPanel', () => {
  it('shows no info when empty', () => {
    render(<PrivateInfoPanel info={{}} />)
    expect(screen.getByText('No private information available yet.')).toBeInTheDocument()
  })

  it('shows info when provided', () => {
    const info = {
      role: 'Washerwoman',
      alignment: 'Good',
      description: 'desc',
      clues: [{ night: 1, text: 'clue1' }],
      known_demon: 'd1',
      known_minions: ['m1', 'm2'],
      demon_bluffs: ['b1', 'b2']
    }
    render(<PrivateInfoPanel info={info} />)
    expect(screen.getByText('Your Role:')).toBeInTheDocument()
    expect(screen.getByText('Washerwoman')).toBeInTheDocument()
    expect(screen.getByText('(Night 1) clue1')).toBeInTheDocument()
    expect(screen.getByText('Known Demon:')).toBeInTheDocument()
    expect(screen.getByText('d1')).toBeInTheDocument()
    expect(screen.getByText('m1, m2')).toBeInTheDocument()
  })
}) 