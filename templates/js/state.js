/**
 * State Module
 * Responsabilidade: gerenciamento centralizadado estado da aplicação
 * - modo atual (repo/user)
 * - task ID
 * - timers
 * - observers/callbacks para mudanças de estado
 */

class StateManager {
  constructor() {
    this.currentMode = 'repo';
    this.currentTaskId = null;
    this.elapsedSecs = 0;
    this.currentStep = -1;
    this.observers = [];
  }

  setMode(mode) {
    this.currentMode = mode;
    this.notifyObservers('modeChanged', mode);
  }

  setTaskId(taskId) {
    this.currentTaskId = taskId;
    this.notifyObservers('taskIdChanged', taskId);
  }

  setElapsedSecs(secs) {
    this.elapsedSecs = secs;
    this.notifyObservers('elapsedSecsChanged', secs);
  }

  incrementElapsedSecs() {
    this.elapsedSecs++;
    this.notifyObservers('elapsedSecsChanged', this.elapsedSecs);
  }

  setCurrentStep(step) {
    if (step === this.currentStep) return;
    this.currentStep = step;
    this.notifyObservers('stepChanged', step);
  }

  subscribe(callback) {
    this.observers.push(callback);
  }

  notifyObservers(event, data) {
    this.observers.forEach(callback => {
      callback(event, data);
    });
  }

  reset() {
    this.currentTaskId = null;
    this.elapsedSecs = 0;
    this.currentStep = -1;
  }
}

export default new StateManager();
