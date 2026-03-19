"use client";

import { useState } from "react";
import { UserPlus, Trash2 } from "lucide-react";
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
  onAddMember,
  onRemoveMember,
  onChangeRole,
}: MemberManagerProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState("editor");
  const [adding, setAdding] = useState(false);

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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Members</h3>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
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
                Add a user to this project by their user ID.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
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
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleAdd} disabled={!userId.trim() || adding}>
                {adding ? "Adding..." : "Add"}
              </Button>
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
