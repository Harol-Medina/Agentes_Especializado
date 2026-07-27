"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

const GITHUB_URL_REGEX =
  /^https:\/\/github\.com\/[a-zA-Z0-9._-]+\/[a-zA-Z0-9._-]+\/?$/;

type FormState = "idle" | "loading" | "error" | "busy";

export function SubmissionForm() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [formState, setFormState] = useState<FormState>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErrorMessage("");

    // Client-side validation
    if (!GITHUB_URL_REGEX.test(repoUrl.trim())) {
      setFormState("error");
      setErrorMessage("Please enter a valid GitHub repository URL (https://github.com/owner/repo)");
      return;
    }

    setFormState("loading");

    try {
      const response = await fetch("/api/v1/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repoUrl: repoUrl.trim() }),
      });

      if (response.status === 202) {
        const data = await response.json();
        router.push(`/analysis/${data.jobId}`);
        return;
      }

      if (response.status === 409) {
        const data = await response.json();
        setFormState("busy");
        setErrorMessage(
          data.message || "An analysis is currently in progress. Please try again later."
        );
        return;
      }

      if (response.status === 400) {
        const data = await response.json();
        setFormState("error");
        setErrorMessage(data.message || "The provided URL is not a valid public GitHub repository.");
        return;
      }

      // Unexpected status
      setFormState("error");
      setErrorMessage("An unexpected error occurred. Please try again.");
    } catch {
      setFormState("error");
      setErrorMessage("Could not connect to the server. Please try again later.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-md space-y-3">
      <div className="flex flex-col gap-2">
        <label
          htmlFor="repo-url"
          className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground"
        >
          Repository URL
        </label>
        <input
          id="repo-url"
          type="text"
          value={repoUrl}
          onChange={(e) => {
            setRepoUrl(e.target.value);
            if (formState === "error" || formState === "busy") {
              setFormState("idle");
              setErrorMessage("");
            }
          }}
          placeholder="https://github.com/owner/repo"
          disabled={formState === "loading"}
          className={cn(
            "w-full px-4 py-2.5 rounded-md",
            "bg-muted border border-border",
            "font-sans text-sm text-foreground placeholder:text-muted-foreground",
            "focus:outline-none focus:ring-2 focus:ring-ring",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "transition-colors duration-150"
          )}
          aria-describedby="url-feedback"
        />
      </div>

      {/* Error / Busy feedback */}
      {errorMessage && (
        <p
          id="url-feedback"
          role="alert"
          className={cn(
            "text-xs font-sans",
            formState === "busy" ? "text-primary" : "text-danger"
          )}
        >
          {formState === "busy" && (
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary mr-1.5 animate-pulse-slow align-middle" />
          )}
          {errorMessage}
        </p>
      )}

      {/* Submit button */}
      <button
        type="submit"
        disabled={formState === "loading" || !repoUrl.trim()}
        className={cn(
          "w-full py-2.5 rounded-[4px]",
          "bg-primary text-primary-foreground",
          "font-sans font-bold text-xs tracking-wider uppercase",
          "hover:opacity-90 transition-opacity duration-150",
          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "flex items-center justify-center gap-2"
        )}
      >
        {formState === "loading" ? (
          <>
            <svg
              className="animate-spin h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Analyzing...
          </>
        ) : (
          "Analyze Repository"
        )}
      </button>
    </form>
  );
}
