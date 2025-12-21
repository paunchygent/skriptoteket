<script setup lang="ts"></script>

<template>
  <div style="padding: 16px">
    <header style="display: flex; gap: 12px; align-items: baseline">
      <h1 style="margin: 0">Skriptoteket SPA</h1>
      <nav style="display: flex; gap: 10px">
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/browse">Browse</RouterLink>
        <RouterLink to="/login">Login</RouterLink>
      </nav>
    </header>
    <main style="margin-top: 16px">
      <RouterView />
    </main>
  </div>
</template>
