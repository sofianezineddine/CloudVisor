# CloudVisor Q Panel

## Overview

The CloudVisor Q Panel is a resizable side panel that provides a natural language interface to CloudVisor's security data. It's powered by the Anthropic Claude API and implements a RAG (Retrieval-Augmented Generation) pipeline.

## Features

- **Resizable Panel**: Drag the right edge to resize from 320px to 90% of screen width
- **Maximize/Minimize**: Toggle between normal and full-screen modes
- **Chat Interface**: Natural language queries with streaming responses
- **Example Queries**: Pre-built example queries to get started
- **Citations**: Source references for all AI-generated responses
- **Suggested Actions**: Actionable next steps based on query results
- **Intent Classification**: Automatically classifies queries into domains (POSTURE, FINDING, COMPLIANCE, etc.)

## Usage

### Opening the Panel

Click the "Ask CloudVisor Q" button in the top navigation bar (next to the search box).

### Sending Queries

1. Type your question in the input field at the bottom
2. Press Enter or click the Send button
3. Wait for the AI response with citations and suggested actions

### Example Queries

- "Which regions is tag cost center=Marketing spending the most in?"
- "How did my costs change month-over-month? Explain why."
- "Do I have over-provisioned EC2 instances?"
- "List S3 buckets with tag value 'production'"

## API Integration

The panel connects to the `/v1/copilot/query` endpoint:

```typescript
POST /v1/copilot/query
{
  "query": "Your natural language question",
  "context": {
    "finding_id": "optional-finding-id",
    "asset_id": "optional-asset-id"
  },
  "stream": false
}
```

### Response Format

```typescript
{
  "query_id": "q_01J...",
  "answer": "AI-generated response",
  "intent": "POSTURE | FINDING | COMPLIANCE | REMEDIATION | THREAT | DRIFT",
  "citations": [
    {
      "source": "findings",
      "reference": "CV-2847",
      "claim": "Description of the claim"
    }
  ],
  "suggested_actions": [
    {
      "label": "View affected assets",
      "action": "navigate",
      "target": "/assets?filter=..."
    }
  ],
  "data_freshness": "2026-04-27T10:32:00Z",
  "processing_ms": 1240
}
```

## Component Props

```typescript
interface CloudVisorQPanelProps {
  isOpen: boolean;      // Controls panel visibility
  onClose: () => void;  // Callback when panel is closed
}
```

## Styling

The panel follows the AWS Cloudscape Design System:
- Uses CSS custom properties from `globals.css`
- Matches AWS Console visual language
- Supports light and dark modes via `[data-theme="dark"]`

## Keyboard Shortcuts

- **Enter**: Send message (Shift+Enter for new line)
- **Escape**: Close panel (when implemented)

## Future Enhancements

- [ ] Streaming responses (SSE)
- [ ] Conversation history persistence
- [ ] Export conversation
- [ ] Voice input
- [ ] Multi-turn context awareness
- [ ] Keyboard shortcuts (Escape to close)
- [ ] Copy message to clipboard
- [ ] Thumbs up/down feedback integration
- [ ] Suggested follow-up questions

## Implementation Details

### State Management

- Panel width stored in component state (not persisted)
- Messages array holds conversation history
- Processing state prevents duplicate submissions

### Resize Logic

- Minimum width: 320px
- Maximum width: 90% of viewport
- Smooth transitions when not actively resizing
- Mouse event handlers for drag-to-resize

### Message Types

- **User messages**: Right-aligned, blue background
- **Assistant messages**: Left-aligned, with Q icon
- **Processing messages**: Animated dots while waiting
- **Error messages**: Red styling (when implemented)

## Dependencies

- React 18+
- lucide-react (icons)
- Next.js 14+ (routing)

## Related Files

- `apps/web/src/components/layout/header.tsx` - Integration point
- `apps/web/src/app/globals.css` - Design tokens
- `services/copilot/` - Backend RAG pipeline (Python)
- `implementation_guide/cloudvisor_q_implementation_guide.md` - Full spec
