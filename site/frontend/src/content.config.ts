import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const baseSchema = z.object({
	title: z.string(),
	description: z.string(),
	pubDate: z.coerce.date(),
	updatedDate: z.coerce.date().optional(),
	fonte: z.string().optional(),
	linkOriginal: z.string().optional(),
	dataOriginal: z.string().optional(),
	imageUrl: z.string().optional(),
	tags: z.array(z.string()).optional(),
});

const orgaosPublicos = defineCollection({
	loader: glob({ base: './src/content/orgaos-publicos', pattern: '**/*.{md,mdx}' }),
	schema: baseSchema,
});

const mercado = defineCollection({
	loader: glob({ base: './src/content/mercado', pattern: '**/*.{md,mdx}' }),
	schema: baseSchema.extend({
		origem: z.string().optional(),
		hashtag: z.string().optional(),
	}),
});

const startupsVc = defineCollection({
	loader: glob({ base: './src/content/startups-vc', pattern: '**/*.{md,mdx}' }),
	schema: baseSchema,
});

const atualizacoes = defineCollection({
	loader: glob({ base: './src/content/atualizacoes', pattern: '**/*.{md,mdx}' }),
	schema: baseSchema,
});

export const collections = {
	orgaosPublicos,
	mercado,
	startupsVc,
	atualizacoes,
};
