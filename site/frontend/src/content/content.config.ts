import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const noticiaSchema = ({ image }: any) =>
  z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    fonte: z.string().optional(),
    linkOriginal: z.string().optional(),
    dataOriginal: z.string().optional(),
    heroImage: z.optional(image()),
  });

const orgaosPublicos = defineCollection({
  loader: glob({ base: './src/content/orgaos-publicos', pattern: '**/*.{md,mdx}' }),
  schema: noticiaSchema,
});

const mercado = defineCollection({
  loader: glob({ base: './src/content/mercado', pattern: '**/*.{md,mdx}' }),
  schema: ({ image }) =>
    z.object({
      title: z.string(),
      description: z.string(),
      pubDate: z.coerce.date(),
      fonte: z.string().optional(),
      linkOriginal: z.string().optional(),
      dataOriginal: z.string().optional(),
      origem: z.string().optional(),
      hashtag: z.string().optional(),
      heroImage: z.optional(image()),
    }),
});

const startupsVc = defineCollection({
  loader: glob({ base: './src/content/startups-vc', pattern: '**/*.{md,mdx}' }),
  schema: noticiaSchema,
});

const atualizacoes = defineCollection({
  loader: glob({ base: './src/content/atualizacoes', pattern: '**/*.{md,mdx}' }),
  schema: noticiaSchema,
});

export const collections = {
  orgaosPublicos,
  mercado,
  startupsVc,
  atualizacoes,
};
