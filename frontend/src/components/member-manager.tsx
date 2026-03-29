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

  const getInitials = (name?: string, email?: string) => {
    const str = name || email || "?";
    return str.split(/[\s@]/).filter(Boolean).slice(0, 2).map(s => s[0]?.toUpperCase()).join("");
  };

  const AVATAR_COLORS = [
    "bg-orange-500/20 text-orange-400",
    "bg-teal-500/20 text-teal-400",
    "bg-pink-500/20 text-pink-400",
    "bg-sky-500/20 text-sky-400",
    "bg-lime-500/20 text-lime-400",
    "bg-violet-500/20 text-violet-400",
  ];

  return (
    <div>
      {/* Add Member button — positioned by parent */}
      <div className="flex items-center justify-end px-4 py-3 border-b border-[var(--border-color)]">
        <Dialog open={dialogOpen} onOpenChange={handleDialogOpen}>
          <DialogTrigger asChild>
            <button className="bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-[11px] font-bold px-4 py-1.5 rounded transition-all active:scale-95 flex items-center gap-2">
              <UserPlus className="h-3.5 w-3.5" />
              Add Member
            </button>
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

      {/* Members table */}
      <table className="w-full text-left">
        <thead className="bg-[var(--surface-high)]/50 border-b border-[var(--border-color)]">
          <tr>
            <th className="px-6 py-3 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Member</th>
            <th className="px-6 py-3 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Role</th>
            <th className="px-6 py-3 text-right text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border-color)]/30">
          {members.length === 0 ? (
            <tr>
              <td colSpan={3} className="px-6 py-8 text-center text-sm text-muted-foreground">
                No members yet
              </td>
            </tr>
          ) : (
            members.map((member, idx) => (
              <tr key={member.id} className="hover:bg-[var(--surface-high)]/30 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs ${AVATAR_COLORS[idx % AVATAR_COLORS.length]}`}>
                      {getInitials(member.name, member.email)}
                    </div>
                    <div>
                      <div className="text-sm font-medium">{member.name || member.user_id}</div>
                      {member.email && (
                        <div className="text-xs text-muted-foreground">{member.email}</div>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <Select
                    value={member.role}
                    onValueChange={(newRole) => onChangeRole(member.user_id, newRole)}
                  >
                    <SelectTrigger className="w-28 bg-transparent border-none text-xs text-[var(--accent-light)] p-0 h-auto hover:text-[var(--accent)] transition-colors">
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
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => handleResetPassword(member.user_id)}
                      title="Generate password reset link"
                      className="text-muted-foreground hover:text-foreground transition-colors p-2"
                    >
                      <KeyRound className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => onRemoveMember(member.user_id)}
                      className="text-muted-foreground hover:text-destructive transition-colors p-2"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
