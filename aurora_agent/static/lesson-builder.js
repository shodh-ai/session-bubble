// Aurora Agent - Interactive Lesson Builder JavaScript
class LessonBuilderState {
    constructor() {
        this.websocket = null;
        this.isConnected = false;
        this.sessionActive = false;
        this.liveActions = [];
        this.lessonSteps = [];
        this.currentLessonId = null;
        this.lessonTitle = '';
        this.lastSaved = null;
        
        this.initializeEventListeners();
        this.initializeDragAndDrop();
    }
    
    initializeEventListeners() {
        // Connection controls
        document.getElementById('connectBtn').addEventListener('click', () => this.connect());
        document.getElementById('startSessionBtn').addEventListener('click', () => this.startSession());
        document.getElementById('stopSessionBtn').addEventListener('click', () => this.stopSession());
        
        // Lesson controls
        document.getElementById('saveLessonBtn').addEventListener('click', () => this.saveLesson());
        document.getElementById('loadLessonBtn').addEventListener('click', () => this.loadLesson());
        document.getElementById('clearLessonBtn').addEventListener('click', () => this.clearLesson());
        
        // Lesson title input
        document.getElementById('lessonTitle').addEventListener('input', (e) => {
            this.lessonTitle = e.target.value;
            this.updateSaveButtonState();
        });
    }
    
    initializeDragAndDrop() {
        const lessonStepsContainer = document.getElementById('lessonSteps');
        this.sortable = Sortable.create(lessonStepsContainer, {
            animation: 150,
            onEnd: (evt) => {
                if (evt.oldIndex !== evt.newIndex) {
                    const movedStep = this.lessonSteps.splice(evt.oldIndex, 1)[0];
                    this.lessonSteps.splice(evt.newIndex, 0, movedStep);
                    this.updateStepNumbers();
                    this.updateSaveButtonState();
                }
            }
        });
    }
    
    connect() {
        const wsUrl = `ws://localhost:8000/ws/session/default_teacher`;
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            this.isConnected = true;
            this.updateConnectionStatus();
            console.log('WebSocket connected');
        };
        
        this.websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
        };
        
        this.websocket.onclose = () => {
            this.isConnected = false;
            this.sessionActive = false;
            this.updateConnectionStatus();
            console.log('WebSocket disconnected');
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    startSession() {
        const spreadsheetUrl = document.getElementById('spreadsheetUrl').value;
        if (!spreadsheetUrl) {
            alert('Please enter a Google Spreadsheet URL');
            return;
        }
        
        if (this.websocket && this.isConnected) {
            this.websocket.send(JSON.stringify({
                command: 'START_SESSION',
                spreadsheet_url: spreadsheetUrl
            }));
        }
    }
    
    stopSession() {
        if (this.websocket && this.isConnected) {
            this.websocket.send(JSON.stringify({
                type: 'STOP_SESSION'
            }));
        }
    }
    
    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'SESSION_STARTED':
                this.sessionActive = true;
                this.updateConnectionStatus();
                this.clearLiveActions();
                break;
                
            case 'HOVER_ANNOTATION':
                this.updateAIThinking(message.element_description);
                break;
                
            case 'VERIFIED_ACTION':
                this.addLiveAction(message);
                break;
        }
    }
    
    updateConnectionStatus() {
        const statusElement = document.getElementById('connectionStatus');
        const startBtn = document.getElementById('startSessionBtn');
        const stopBtn = document.getElementById('stopSessionBtn');
        
        if (this.sessionActive) {
            statusElement.textContent = 'Session Active';
            statusElement.style.color = '#4285f4';
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else if (this.isConnected) {
            statusElement.textContent = 'Connected';
            statusElement.style.color = '#34a853';
            startBtn.disabled = false;
            stopBtn.disabled = true;
        } else {
            statusElement.textContent = 'Disconnected';
            statusElement.style.color = '#ea4335';
            startBtn.disabled = true;
            stopBtn.disabled = true;
        }
    }
    
    updateAIThinking(description) {
        const thinkingContent = document.getElementById('aiThinkingContent');
        thinkingContent.textContent = description;
    }
    
    addLiveAction(actionData) {
        const actionId = Date.now() + Math.random();
        const action = {
            id: actionId,
            ...actionData,
            timestamp: new Date().toLocaleTimeString(),
            addedToLesson: false
        };
        
        this.liveActions.unshift(action);
        this.renderLiveActions();
    }
    
    renderLiveActions() {
        const container = document.getElementById('liveActions');
        
        if (this.liveActions.length === 0) {
            container.innerHTML = '<div class="empty-state">Start session to see live actions</div>';
            return;
        }
        
        container.innerHTML = this.liveActions.map(action => `
            <div class="action-item">
                <button class="add-to-lesson-btn" 
                        onclick="lessonBuilder.addToLesson('${action.id}')"
                        ${action.addedToLesson ? 'disabled' : ''}>
                    ${action.addedToLesson ? '✓ Added' : '+ Add to Lesson'}
                </button>
                
                <div style="margin-bottom: 10px;">
                    <span style="background: ${action.status === 'SUCCESS' ? '#e8f5e8' : '#ffebee'}; 
                                 color: ${action.status === 'SUCCESS' ? '#2e7d32' : '#c62828'}; 
                                 padding: 4px 12px; border-radius: 20px; font-size: 0.8rem;">
                        ${action.status === 'SUCCESS' ? '✅ SUCCESS' : '❌ FAILED'}
                    </span>
                    <span style="float: right; color: #999; font-size: 0.8rem;">${action.timestamp}</span>
                </div>
                
                <div style="font-weight: 500; margin-bottom: 8px;">
                    ${action.interpretation || action.description || 'Action detected'}
                </div>
                
                <div style="color: #666; font-size: 0.9rem;">
                    ${action.verification || action.message || 'No additional details'}
                </div>
            </div>
        `).join('');
    }
    
    addToLesson(actionId) {
        const action = this.liveActions.find(a => a.id == actionId);
        if (!action || action.addedToLesson) return;
        
        action.addedToLesson = true;
        
        const step = {
            id: Date.now() + Math.random(),
            stepNumber: this.lessonSteps.length + 1,
            narration: this.generateDefaultNarration(action),
            actionData: action,
            timestamp: new Date().toISOString()
        };
        
        this.lessonSteps.push(step);
        this.renderLiveActions();
        this.renderLessonSteps();
        this.updateStepCount();
        this.updateSaveButtonState();
    }
    
    generateDefaultNarration(action) {
        const description = action.interpretation || action.description || 'Perform this action';
        return `Step ${this.lessonSteps.length + 1}: ${description}`;
    }
    
    renderLessonSteps() {
        const container = document.getElementById('lessonSteps');
        
        if (this.lessonSteps.length === 0) {
            container.innerHTML = '<div class="empty-state">Add actions to build lesson plan</div>';
            return;
        }
        
        container.innerHTML = this.lessonSteps.map((step, index) => `
            <div class="lesson-step" data-step-id="${step.id}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="background: #4285f4; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem;">
                        Step ${index + 1}
                    </span>
                    <div>
                        <button onclick="lessonBuilder.editStep('${step.id}')" style="padding: 4px 8px; margin-right: 5px; background: #ffc107; border: none; border-radius: 4px; cursor: pointer;">✏️</button>
                        <button onclick="lessonBuilder.deleteStep('${step.id}')" style="padding: 4px 8px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">🗑️</button>
                    </div>
                </div>
                
                <textarea class="step-narration" 
                          data-step-id="${step.id}"
                          onchange="lessonBuilder.updateNarration('${step.id}', this.value)"
                          placeholder="Add narration for this step...">${step.narration}</textarea>
                
                <div style="background: #e3f2fd; padding: 8px 12px; border-radius: 4px; font-size: 0.85rem; color: #1565c0; margin-top: 10px;">
                    📋 ${step.actionData.interpretation || step.actionData.description || 'Action details'}
                </div>
            </div>
        `).join('');
    }
    
    updateNarration(stepId, narration) {
        const step = this.lessonSteps.find(s => s.id == stepId);
        if (step) {
            step.narration = narration;
            this.updateSaveButtonState();
        }
    }
    
    editStep(stepId) {
        const textarea = document.querySelector(`textarea[data-step-id="${stepId}"]`);
        if (textarea) {
            textarea.focus();
            textarea.select();
        }
    }
    
    deleteStep(stepId) {
        if (confirm('Are you sure you want to delete this step?')) {
            this.lessonSteps = this.lessonSteps.filter(s => s.id != stepId);
            this.renderLessonSteps();
            this.updateStepNumbers();
            this.updateStepCount();
            this.updateSaveButtonState();
        }
    }
    
    updateStepNumbers() {
        this.lessonSteps.forEach((step, index) => {
            step.stepNumber = index + 1;
        });
        this.renderLessonSteps();
    }
    
    updateStepCount() {
        document.getElementById('stepCount').textContent = this.lessonSteps.length;
    }
    
    updateSaveButtonState() {
        const saveBtn = document.getElementById('saveLessonBtn');
        const hasTitle = this.lessonTitle.trim().length > 0;
        const hasSteps = this.lessonSteps.length > 0;
        
        saveBtn.disabled = !(hasTitle && hasSteps);
    }
    
    clearLiveActions() {
        this.liveActions = [];
        this.renderLiveActions();
    }
    
    async saveLesson() {
        if (!this.lessonTitle.trim() || this.lessonSteps.length === 0) {
            alert('Please add a lesson title and at least one step');
            return;
        }
        
        const lessonData = {
            title: this.lessonTitle,
            steps: this.lessonSteps.map((step, index) => ({
                step_number: index + 1,
                narration: step.narration,
                action_data: step.actionData
            })),
            created_at: new Date().toISOString(),
            creator_id: 'default_teacher'
        };
        
        try {
            const response = await fetch('/api/lessons', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(lessonData)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.currentLessonId = result.lesson_id;
                this.lastSaved = new Date().toLocaleTimeString();
                document.getElementById('lastSaved').textContent = this.lastSaved;
                alert('Lesson saved successfully!');
            } else {
                throw new Error('Failed to save lesson');
            }
        } catch (error) {
            console.error('Save error:', error);
            alert('Failed to save lesson. Please try again.');
        }
    }
    
    async loadLesson() {
        const lessonId = prompt('Enter lesson ID to load:');
        if (!lessonId) return;
        
        try {
            const response = await fetch(`/api/lessons/${lessonId}`);
            if (response.ok) {
                const lessonData = await response.json();
                this.loadLessonData(lessonData);
            } else {
                throw new Error('Lesson not found');
            }
        } catch (error) {
            console.error('Load error:', error);
            alert('Failed to load lesson. Please check the lesson ID.');
        }
    }
    
    loadLessonData(lessonData) {
        this.currentLessonId = lessonData.lesson_id;
        this.lessonTitle = lessonData.title;
        this.lessonSteps = lessonData.steps.map(step => ({
            id: Date.now() + Math.random(),
            stepNumber: step.step_number,
            narration: step.narration,
            actionData: step.action_data,
            timestamp: new Date().toISOString()
        }));
        
        document.getElementById('lessonTitle').value = this.lessonTitle;
        this.renderLessonSteps();
        this.updateStepCount();
        this.updateSaveButtonState();
    }
    
    clearLesson() {
        if (confirm('Are you sure you want to clear the current lesson plan?')) {
            this.lessonSteps = [];
            this.lessonTitle = '';
            this.currentLessonId = null;
            this.lastSaved = null;
            
            document.getElementById('lessonTitle').value = '';
            document.getElementById('lastSaved').textContent = 'Never';
            
            this.renderLessonSteps();
            this.updateStepCount();
            this.updateSaveButtonState();
        }
    }
}

// Initialize the lesson builder when page loads
let lessonBuilder;
document.addEventListener('DOMContentLoaded', () => {
    lessonBuilder = new LessonBuilderState();
});
