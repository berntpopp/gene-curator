# Enhancement: Real-Time Progress Tracking via WebSocket

**Priority**: Low-Medium
**Complexity**: Medium-High
**Estimated Effort**: 6-8 hours
**Reference**: `kidney-genetics-db/backend/app/core/progress_tracker.py` (453 lines)

## Overview

Implement a WebSocket-based progress tracking system for long-running operations (curation pipeline, bulk imports, scoring calculations). Provides real-time updates to the frontend without polling, improving user experience for async tasks.

## Current State

- No real-time progress tracking for long-running operations
- Frontend must poll API for status updates (inefficient)
- No visibility into multi-step workflow progress
- Poor UX for operations taking >10 seconds

## Proposed Implementation

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ Frontend (Vue 3)                                    │
│ WebSocket connection for real-time updates         │
└────────────────┬────────────────────────────────────┘
                 │ ws://localhost:8001/ws/progress
┌────────────────▼────────────────────────────────────┐
│ Backend (FastAPI)                                   │
│ ┌──────────────┐      ┌──────────────────────┐    │
│ │ WebSocket    │ ───> │ Event Bus (PubSub)   │    │
│ │ Manager      │      └──────────────────────┘    │
│ └──────────────┘              ▲                    │
│                               │                    │
│ ┌──────────────┐      ┌──────┴───────────┐       │
│ │ Progress     │ ───> │ DataSource       │       │
│ │ Tracker      │      │ Progress Table   │       │
│ └──────────────┘      └──────────────────┘       │
└─────────────────────────────────────────────────────┘
```

### Core Components

**1. ProgressTracker Class** (`backend/app/core/progress_tracker.py`)

```python
from contextlib import contextmanager
from app.core.events import event_bus, EventTypes

class ProgressTracker:
    """Track and report progress for long-running operations"""

    def __init__(self, db: Session, source_name: str):
        self.db = db
        self.source_name = source_name
        self.progress_record = self._get_or_create_progress()
        self._update_interval = 1.0  # Update database every second
        self._last_update_time = datetime.now(timezone.utc)

    @contextmanager
    def track_operation(self, operation_name: str):
        """Context manager for tracking an operation"""
        self.start(operation_name)
        try:
            yield self
        except Exception as e:
            self.error(str(e))
            raise
        finally:
            if self.progress_record.status == SourceStatus.running:
                self.complete()

    def start(self, operation: str):
        """Mark operation as started"""
        self.progress_record.status = SourceStatus.running
        self.progress_record.current_operation = operation
        self.progress_record.started_at = datetime.now(timezone.utc)
        self.progress_record.items_processed = 0
        self.progress_record.progress_percentage = 0.0
        self._commit_and_broadcast()

    def update(
        self,
        current_item: int | None = None,
        total_items: int | None = None,
        items_added: int | None = None,
        items_failed: int | None = None,
        operation: str | None = None,
        force: bool = False
    ):
        """Update progress (rate-limited to 1/second unless forced)"""
        # Update counters
        if items_added: self.progress_record.items_added += items_added
        if items_failed: self.progress_record.items_failed += items_failed
        if current_item: self.progress_record.current_item = current_item
        if total_items: self.progress_record.total_items = total_items

        # Calculate percentage
        if total_items and total_items > 0:
            self.progress_record.progress_percentage = (current_item / total_items * 100)

        # Commit if enough time passed or forced
        now = datetime.now(timezone.utc)
        if force or (now - self._last_update_time).total_seconds() >= self._update_interval:
            self._commit_and_broadcast()
            self._last_update_time = now

    def complete(self, operation: str = "Operation completed"):
        """Mark operation as completed"""
        self.progress_record.status = SourceStatus.completed
        self.progress_record.progress_percentage = 100.0
        self.progress_record.completed_at = datetime.now(timezone.utc)
        self._commit_and_broadcast()

    def error(self, error_message: str):
        """Mark operation as failed"""
        self.progress_record.status = SourceStatus.failed
        self.progress_record.error_message = error_message
        self._commit_and_broadcast()

    def _commit_and_broadcast(self):
        """Commit to DB and publish event to event bus"""
        self.db.commit()

        # Publish to event bus (WebSocket manager subscribes)
        progress_data = self.progress_record.to_dict()
        event_type = EventTypes.PROGRESS_UPDATE

        try:
            asyncio.create_task(event_bus.publish(event_type, progress_data))
        except RuntimeError:
            pass  # Not in async context
```

**2. Event Bus** (`backend/app/core/events.py`)

```python
from typing import Callable, Dict, List
import asyncio

class EventTypes:
    """Event type constants"""
    PROGRESS_UPDATE = "progress_update"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

class EventBus:
    """Simple pub/sub event bus for progress updates"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    async def publish(self, event_type: str, data: dict):
        """Publish event to all subscribers"""
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Event callback failed: {e}")

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

# Global event bus
event_bus = EventBus()
```

**3. WebSocket Manager** (`backend/app/api/v1/endpoints/websocket.py`)

```python
from fastapi import WebSocket, WebSocketDisconnect
from app.core.events import event_bus, EventTypes

class WebSocketManager:
    """Manage WebSocket connections for progress updates"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections[:]:  # Copy to avoid modification during iteration
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast failed: {e}")
                self.disconnect(connection)

# Global WebSocket manager
ws_manager = WebSocketManager()

# Subscribe to event bus
async def _progress_broadcast(data: dict):
    """Broadcast progress updates via WebSocket"""
    await ws_manager.broadcast({
        "type": "progress_update",
        "data": data
    })

event_bus.subscribe(EventTypes.PROGRESS_UPDATE, _progress_broadcast)
event_bus.subscribe(EventTypes.TASK_COMPLETED, _progress_broadcast)
event_bus.subscribe(EventTypes.TASK_FAILED, _progress_broadcast)

# WebSocket endpoint
@router.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for progress updates"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
```

**4. Database Schema**

```sql
-- Progress tracking table
CREATE TABLE IF NOT EXISTS operation_progress (
    id SERIAL PRIMARY KEY,
    operation_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- running, completed, failed
    current_operation TEXT,
    progress_percentage FLOAT DEFAULT 0.0,
    current_item INTEGER DEFAULT 0,
    total_items INTEGER,
    items_added INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    estimated_completion TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_operation_status (operation_name, status)
);
```

### Frontend Integration (Vue 3)

**Progress Store** (`frontend/src/stores/progress.js`)

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useProgressStore = defineStore('progress', () => {
  const operations = ref({})
  const ws = ref(null)

  function connect() {
    const wsUrl = `ws://localhost:8001/ws/progress`
    ws.value = new WebSocket(wsUrl)

    ws.value.onmessage = (event) => {
      const message = JSON.parse(event.data)
      if (message.type === 'progress_update') {
        const { operation_name, ...data } = message.data
        operations.value[operation_name] = data
      }
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.value.onclose = () => {
      // Reconnect after 5 seconds
      setTimeout(connect, 5000)
    }
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close()
    }
  }

  const getOperation = (name) => computed(() => operations.value[name])

  return { operations, connect, disconnect, getOperation }
})
```

**Progress Component** (`frontend/src/components/ProgressBar.vue`)

```vue
<template>
  <v-card v-if="progress">
    <v-card-title>{{ progress.current_operation }}</v-card-title>
    <v-card-text>
      <v-progress-linear
        :model-value="progress.progress_percentage"
        color="primary"
        height="25"
      >
        <template #default>
          <strong>{{ Math.ceil(progress.progress_percentage) }}%</strong>
        </template>
      </v-progress-linear>

      <div class="mt-2">
        <small>
          {{ progress.current_item }} / {{ progress.total_items }} items
          • Added: {{ progress.items_added }}
          • Failed: {{ progress.items_failed }}
        </small>
      </div>

      <div v-if="progress.estimated_completion" class="mt-1">
        <small>
          Estimated completion: {{ formatTime(progress.estimated_completion) }}
        </small>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import { useProgressStore } from '@/stores/progress'

const props = defineProps({
  operationName: String
})

const progressStore = useProgressStore()
const progress = progressStore.getOperation(props.operationName)

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString()
}
</script>
```

### Usage Pattern

**Backend: Long-running operation**

```python
from app.core.progress_tracker import ProgressTracker

async def process_curation_pipeline(db: Session, scope_id: int):
    """Process all curations in a scope with progress tracking"""
    tracker = ProgressTracker(db, operation_name=f"curation_pipeline_scope_{scope_id}")

    with tracker.track_operation("Processing curations"):
        curations = get_curations(db, scope_id)
        total = len(curations)

        for i, curation in enumerate(curations):
            try:
                # Process curation
                result = process_curation(curation)

                # Update progress
                tracker.update(
                    current_item=i + 1,
                    total_items=total,
                    items_added=1 if result.is_new else 0,
                    operation=f"Processing curation {curation.id}"
                )
            except Exception as e:
                tracker.update(items_failed=1)
                logger.error(f"Failed to process curation {curation.id}: {e}")

        # Automatic completion via context manager
```

**Frontend: Subscribe to progress**

```vue
<template>
  <div>
    <v-btn @click="startPipeline">Start Pipeline</v-btn>
    <progress-bar operation-name="curation_pipeline_scope_1" />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useProgressStore } from '@/stores/progress'
import ProgressBar from '@/components/ProgressBar.vue'
import api from '@/services/api'

const progressStore = useProgressStore()

onMounted(() => {
  progressStore.connect()  // Connect WebSocket
})

onUnmounted(() => {
  progressStore.disconnect()
})

async function startPipeline() {
  await api.post('/api/v1/pipeline/start', { scope_id: 1 })
  // Progress updates arrive automatically via WebSocket
}
</script>
```

## Implementation Steps

1. **Create progress tracking components**
   - `backend/app/core/progress_tracker.py` (453 lines)
   - `backend/app/core/events.py` (100 lines)
   - `backend/app/models/progress.py` (SQLAlchemy model)

2. **Add WebSocket support**
   - `backend/app/api/v1/endpoints/websocket.py` (WebSocket manager)
   - Add WebSocket route to FastAPI app
   - Install `websockets` dependency

3. **Create database migration**
   ```bash
   cd database/sql
   # Add operation_progress table to schema
   ```

4. **Frontend integration**
   - Create `frontend/src/stores/progress.js` (Pinia store)
   - Create `frontend/src/components/ProgressBar.vue`
   - Connect WebSocket on app mount

5. **Integrate with existing operations**
   - Curation pipeline
   - Bulk gene imports
   - Scoring calculations
   - Schema validation

## Benefits

- **Real-Time UX**: Users see live progress without polling
- **Performance**: WebSocket more efficient than polling
- **Observability**: Track all long-running operations
- **Error Handling**: Immediate feedback on failures

## Testing

```python
# tests/integration/test_progress_tracking.py
async def test_progress_tracking_context_manager():
    tracker = ProgressTracker(db, "test_operation")

    with tracker.track_operation("Test"):
        tracker.update(current_item=5, total_items=10)

    progress = db.query(OperationProgress).filter_by(operation_name="test_operation").first()
    assert progress.status == "completed"
    assert progress.progress_percentage == 100.0

async def test_websocket_broadcast(websocket_client):
    # Connect WebSocket
    async with websocket_client as ws:
        # Trigger progress update
        tracker.update(current_item=1, total_items=10)

        # Receive WebSocket message
        message = await ws.receive_json()
        assert message["type"] == "progress_update"
        assert message["data"]["progress_percentage"] == 10.0
```

## Dependencies

- FastAPI WebSocket support (built-in)
- Vue 3 + Pinia (already in project)
- No additional Python dependencies

## References

- kidney-genetics-db: `backend/app/core/progress_tracker.py` (453 lines)
- Production: 100% WebSocket stability during 30min pipeline runs
- Event bus pattern: Decouples progress tracking from WebSocket

## Acceptance Criteria

- [ ] ProgressTracker class with context manager support
- [ ] Event bus for pub/sub progress updates
- [ ] WebSocket manager and /ws/progress endpoint
- [ ] operation_progress table created
- [ ] Frontend progress store (Pinia) implemented
- [ ] ProgressBar Vue component created
- [ ] At least one long-running operation integrated (e.g., scoring)
- [ ] WebSocket reconnection logic working
- [ ] Unit tests for ProgressTracker
- [ ] Integration test for WebSocket broadcast
