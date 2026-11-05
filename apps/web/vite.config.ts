import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Caminhos relativos e rotas por hash permitem hospedar o mesmo build em subdiretórios.
export default defineConfig({ plugins: [react()], base: './' });
