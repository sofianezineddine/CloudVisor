# ─── CloudVisor Web — Production Image ─────────────────────────────────────────
# Uses pre-built Next.js standalone output
FROM node:20-alpine

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy the standalone build output
COPY .next/standalone ./
COPY .next/static ./.next/static
COPY public ./public

# Set ownership
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
