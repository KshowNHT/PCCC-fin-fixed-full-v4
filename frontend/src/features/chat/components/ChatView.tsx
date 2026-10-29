import React from "react";
import { ChatMessage } from "../../../types";
import { MessageList } from "./MessageList";
import { QuickPrompts } from "./QuickPrompts";
import { ChatInput } from "./ChatInput";

interface ChatViewProps {
  messages: ChatMessage[];
  isPending: boolean;
  onSendMessage: (text: string) => void;
  onCancelPending?: () => void;
  onOpenOcrUpload: () => void;
}

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  isPending,
  onSendMessage,
  onCancelPending,
  onOpenOcrUpload,
}) => {
  return (
    <div className="flex-1 flex flex-col h-full bg-slate-50/50 dark:bg-slate-950/60 overflow-hidden relative">
      <MessageList
        messages={messages}
        isPending={isPending}
        onOpenOcrUpload={onOpenOcrUpload}
      />

      <QuickPrompts
        onSelectPrompt={onSendMessage}
        disabled={isPending}
      />

      <ChatInput
        onSendMessage={onSendMessage}
        isPending={isPending}
        onCancelPending={onCancelPending}
        onOpenOcrUpload={onOpenOcrUpload}
      />
    </div>
  );
};

