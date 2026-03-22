"use client";

import { useState } from "react";
import { UserPlus, Trash2, KeyRound, Copy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";

interface Member {
  id: string;
  user_id: string;
  role: string;
  name?: string;
  email?: string;
  created_at: string;
}

interface MemberManagerProps {
  members: Member[];
  projectSlug: string;
  orgSlug: string;
  onAddMember: (userId: string, role: string) => Promise<void>;
  onRemoveMember: (userId: string) => Promise<void>;
  onChangeRole: (userId: string, role: string) => Promise<void>;
}

const ROLES = ["owner", "admin", "editor", "commenter", "viewer"] as const;

const ROLE_COLORS: Record<string, string> = {
  owner: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  admin: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  editor: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  commenter: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  viewer: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
};

export function MemberManager({
  members,
  orgSlug,
  onAddMember,
  onRemoveMember,
  onChangeRole,
}: MemberManagerProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [tab, setTab] = useState<"existing" | "create">("existing");
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState("editor");
  const [adding, setAdding] = useState(false);

  // Create user form
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [creating, setCreating] = useState(false);

  const handleAdd = async () => {
    if (!userId.trim()) return;
    setAdding(true);
    try {
      await onAddMember(userId.trim(), role);
      setDialogOpen(false);
      setUserId("");
      setRole("editor");
    } finally {
      setAdding(false);
    }
  };

  const handleCreateUser = async () => {
    if (!newName.trim() || !newEmail.trim() || !newPassword.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(`/api/orgs/${orgSlug}/members/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newName.trim(),
          email: newEmail.trim(),
          password: newPassword.trim(),
          role,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        toast.error(data.error || "Failed to create user");
        return;
      }
      const data = await res.json();
      toast.success(`User "${data.user.name}" created`);

      // Auto-add the new user as a project member
      try {
        await onAddMember(data.user.id, role);
      } catch {
        toast.error("User created but failed to add as project member. Add manually by UUID: " + data.user.id);
      }

      setDialogOpen(false);
      setNewName("");
      setNewEmail("");
      setNewPassword("");
      setRole("editor");
    } finally {
      setCreating(false);
    }
  };

  const handleResetPassword = async (memberId: string) => {
    try {
      const res = await fetch(
        `/api/orgs/${orgSlug}/members/${memberId}/reset-password`,
        { method: "POST" }
      );
      if (!res.ok) {
        const data = await res.json();
        toast.error(data.error || "Failed to generate reset link");
        return;
      }
      const data = await res.json();
      const fullUrl = `${window.location.origin}${data.reset_url}`;
      await navigator.clipboard.writeText(fullUrl);
      toast.success("Reset URL copied to clipboard", {
        description: `Expires: ${new Date(data.expires_at).toLocaleString()}`,
      });
    } catch {
      toast.error("Failed to generate reset link");
    }
  };

  const handleDialogOpen = (open: boolean) => {
    setDialogOpen(open);
    if (!open) {
      setTab("existing");
      setUserId("");
      setNewName("");
      setNewEmail("");
      setNewPassword("");
      setRole("editor");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Members</h3>
        <Dialog open={dialogOpen} onOpenChange={handleDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <UserPlus className="mr-1.5 h-4 w-4" />
              Add Member
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Member</DialogTitle>
              <DialogDescription>
                Add an existing user by ID or create a new user account.
              </DialogDescription>
            </DialogHeader>

            <div className="flex gap-1 rounded-lg bg-muted p-1">
              <button
                onClick={() => setTab("existing")}
                className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  tab === "existing"
                    ? "bg-background shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Existing User
              </button>
              <button
                onClick={() => setTab("create")}
                className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  tab === "create"
                    ? "bg-background shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Create User
              </button>
            </div>

            <div className="space-y-4 py-2">
              {tab === "existing" ? (
                <div>
                  <label htmlFor="member-id" className="text-sm font-medium">
                    User ID
                  </label>
                  <Input
                    id="member-id"
                    placeholder="User UUID"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    className="mt-1.5"
                  />
                </div>
              ) : (
                <>
                  <div>
                    <label htmlFor="new-name" className="text-sm font-medium">
                      Name
                    </label>
                    <Input
                      id="new-name"
                      placeholder="Full name"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      className="mt-1.5"
                    />
                  </div>
                  <div>
                    <label htmlFor="new-email" className="text-sm font-medium">
                      Email
                    </label>
                    <Input
                      id="new-email"
                      type="email"
                      placeholder="user@example.com"
                      value={newEmail}
                      onChange={(e) => setNewEmail(e.target.value)}
                      className="mt-1.5"
                    />
                  </div>
                  <div>
                    <label htmlFor="new-password" className="text-sm font-medium">
                      Password
                    </label>
                    <Input
                      id="new-password"
                      type="password"
                      placeholder="Initial password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="mt-1.5"
                    />
                  </div>
                </>
              )}
              <div>
                <label className="text-sm font-medium">Role</label>
                <Select value={role} onValueChange={setRole}>
                  <SelectTrigger className="mt-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map((r) => (
                      <SelectItem key={r} value={r}>
                        {r.charAt(0).toUpperCase() + r.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => handleDialogOpen(false)}>
                Cancel
              </Button>
              {tab === "existing" ? (
                <Button onClick={handleAdd} disabled={!userId.trim() || adding}>
                  {adding ? "Adding..." : "Add"}
                </Button>
              ) : (
                <Button
                  onClick={handleCreateUser}
                  disabled={
                    !newName.trim() ||
                    !newEmail.trim() ||
                    !newPassword.trim() ||
                    creating
                  }
                >
                  {creating ? "Creating..." : "Create & Add"}
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="divide-y rounded-lg border">
        {members.length === 0 ? (
          <div className="p-4 text-center text-sm text-muted-foreground">
            No members yet
          </div>
        ) : (
          members.map((member) => (
            <div
              key={member.id}
              className="flex items-center justify-between p-3"
            >
              <div className="flex items-center gap-3">
                <div>
                  <p className="text-sm font-medium">
                    {member.name || member.email || member.user_id}
                  </p>
                  {member.email && (
                    <p className="text-xs text-muted-foreground">
                      {member.email}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Select
                  value={member.role}
                  onValueChange={(newRole) =>
                    onChangeRole(member.user_id, newRole)
                  }
                >
                  <SelectTrigger className="w-32">
                    <Badge
                      className={ROLE_COLORS[member.role] || ""}
                      variant="secondary"
                    >
                      {member.role}
                    </Badge>
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map((r) => (
                      <SelectItem key={r} value={r}>
                        {r.charAt(0).toUpperCase() + r.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleResetPassword(member.user_id)}
                  aria-label="Reset password"
                  title="Generate password reset link"
                >
                  <KeyRound className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onRemoveMember(member.user_id)}
                  aria-label="Remove member"
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
