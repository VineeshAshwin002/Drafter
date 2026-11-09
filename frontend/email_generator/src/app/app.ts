import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, ElementRef, ViewChild, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

interface ChatMessage {
  role: 'assistant' | 'user';
  content: string;
}

interface EmailResponse {
  thread_id: string;
  status: string;
  email_draft?: string;
  question?: string;
  filename?: string;
}

@Component({
  selector: 'app-root',
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  @ViewChild('messageList') private messageList?: ElementRef<HTMLElement>;

  private readonly http = inject(HttpClient);
  private readonly changeDetector = inject(ChangeDetectorRef);
  private readonly apiUrl = 'http://localhost:8000';

  protected messages: ChatMessage[] = [
    {
      role: 'assistant',
      content: 'Tell me what email you would like me to draft.'
    }
  ];
  protected request = '';
  protected updateRequest = '';
  protected lastRequest = '';
  protected draft = '';
  protected question = '';
  protected threadId = '';
  protected isWaiting = false;
  protected isReviewing = false;
  protected copied = false;
  protected error = '';
  protected loadingLabel = 'Creating your email...';

  protected async sendRequest(): Promise<void> {
    const request = this.request.trim();
    if (!request || this.isWaiting) {
      return;
    }

    this.addMessage('user', request);
    this.lastRequest = request;
    this.request = '';
    this.error = '';
    this.loadingLabel = 'Creating your email...';
    this.isWaiting = true;

    try {
      const response = await firstValueFrom(
        this.http.post<EmailResponse>(`${this.apiUrl}/emails`, {
          user_request: request
        })
      );
      this.handleEmailResponse(response);
    } catch (error) {
      this.error = this.getErrorMessage(error, 'Unable to reach the email service. Please try again.');
    } finally {
      this.isWaiting = false;
    }
  }

  protected async regenerate(): Promise<void> {
    if (!this.lastRequest || this.isWaiting) {
      return;
    }

    this.error = '';
    this.loadingLabel = 'Regenerating your email...';
    this.isWaiting = true;

    try {
      const response = await firstValueFrom(
        this.http.post<EmailResponse>(`${this.apiUrl}/emails`, {
          user_request: this.lastRequest
        })
      );
      this.handleEmailResponse(response);
    } catch (error) {
      this.error = this.getErrorMessage(error, 'Unable to regenerate the email. Please try again.');
    } finally {
      this.isWaiting = false;
    }
  }

  protected async updateEmail(): Promise<void> {
    const update = this.updateRequest.trim();
    if (!update || !this.threadId || this.isWaiting) {
      return;
    }

    this.addMessage('user', update);
    this.updateRequest = '';
    this.error = '';
    this.loadingLabel = 'Updating your email...';
    this.isWaiting = true;

    try {
      const response = await firstValueFrom(
        this.http.post<EmailResponse>(`${this.apiUrl}/emails/${this.threadId}/review`, {
          answer: 'yes',
          request: update
        })
      );
      this.handleEmailResponse(response);
    } catch (error) {
      this.error = this.getErrorMessage(error, 'Unable to update the email. Please try again.');
    } finally {
      this.isWaiting = false;
    }
  }

  protected async copyDraft(): Promise<void> {
    if (!this.draft) {
      return;
    }

    try {
      await navigator.clipboard.writeText(this.draft);
      this.copied = true;
      window.setTimeout(() => {
        this.copied = false;
      }, 1800);
    } catch {
      this.error = 'Unable to copy the email draft.';
    }
  }

  private handleEmailResponse(response: EmailResponse): void {
    this.threadId = response.thread_id;
    this.draft = response.email_draft ?? '';
    this.copied = false;
    this.question = response.question ?? '';
    this.isReviewing = response.status === 'awaiting_update_confirmation';

    if (this.draft) {
      this.addMessage('assistant', 'Here is your email draft.');
    }
    if (this.isReviewing) {
      this.addMessage('assistant', this.question || 'Do you want to update the email?');
    }
    this.changeDetector.detectChanges();
  }

  private addMessage(role: ChatMessage['role'], content: string): void {
    this.messages = [...this.messages, { role, content }];
    setTimeout(() => this.scrollToLatest());
  }

  private scrollToLatest(): void {
    const element = this.messageList?.nativeElement;
    if (element) {
      element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' });
    }
  }

  private getErrorMessage(error: unknown, fallback: string): string {
    const response = (error as { error?: { detail?: string } }).error;
    return response?.detail || fallback;
  }
}
