<script>
	import { onMount } from 'svelte';
	import Tools from '$lib/components/workspace/Tools.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				tools.set(await getTools(localStorage.token));
			})()
		]);
	});
</script>

{#if $tools !== null}
	<Tools />
{/if}
