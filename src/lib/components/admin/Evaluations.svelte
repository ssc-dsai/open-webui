<script>
	import { getContext, tick, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Leaderboard from './Evaluations/Leaderboard.svelte';
	import Feedbacks from './Evaluations/Feedbacks.svelte';

	import { getAllFeedbacks } from '$lib/apis/evaluations';

	const i18n = getContext('i18n');

	let selectedTab = 'leaderboard';

	type Feedback = {
		model_id: string;
		sibling_model_ids?: string[];
		rating: number;
	};

	type ModelStats = {
		rating: number;
		won: number;
		draw: number;
		lost: number;
	};

	function calculateModelStats(feedbacks: Feedback[]): Map<string, ModelStats> {
		const stats = new Map<string, ModelStats>();
		const K = 32;

		function getOrDefaultStats(modelId: string): ModelStats {
			return stats.get(modelId) || { rating: 1000, won: 0, draw: 0, lost: 0 };
		}

		function updateStats(modelId: string, ratingChange: number, outcome: number) {
			const currentStats = getOrDefaultStats(modelId);
			currentStats.rating += ratingChange;
			if (outcome === 1) currentStats.won++;
			else if (outcome === 0.5) currentStats.draw++;
			else if (outcome === 0) currentStats.lost++;
			stats.set(modelId, currentStats);
		}

		function calculateEloChange(ratingA: number, ratingB: number, outcome: number): number {
			const expectedScore = 1 / (1 + Math.pow(10, (ratingB - ratingA) / 400));
			return K * (outcome - expectedScore);
		}

		feedbacks.forEach((feedback) => {
			const modelA = feedback.data.model_id;
			const statsA = getOrDefaultStats(modelA);
			let outcome: number;

			switch (feedback.data.rating.toString()) {
				case '1':
					outcome = 1;
					break;
				case '0':
					outcome = 0.5;
					break;
				case '-1':
					outcome = 0;
					break;
				default:
					return; // Skip invalid ratings
			}

			const opponents = feedback.data.sibling_model_ids || [];
			opponents.forEach((modelB) => {
				const statsB = getOrDefaultStats(modelB);
				const changeA = calculateEloChange(statsA.rating, statsB.rating, outcome);
				const changeB = calculateEloChange(statsB.rating, statsA.rating, 1 - outcome);

				updateStats(modelA, changeA, outcome);
				updateStats(modelB, changeB, 1 - outcome);
			});
		});

		return stats;
	}

	let loaded = false;
	let feedbacks = [];

	onMount(async () => {
		feedbacks = await getAllFeedbacks(localStorage.token);
		loaded = true;

		const containerElement = document.getElementById('users-tabs-container');

		if (containerElement) {
			containerElement.addEventListener('wheel', function (event) {
				if (event.deltaY !== 0) {
					// Adjust horizontal scroll position based on vertical scroll
					containerElement.scrollLeft += event.deltaY;
				}
			});
		}
	});
</script>

{#if loaded}
	<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
		<div
			id="users-tabs-container"
			class="tabs flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-40 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
		>
			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab ===
				'leaderboard'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedTab = 'leaderboard';
				}}
			>
				<div class=" self-center mr-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm6 5.75a.75.75 0 0 1 1.5 0v3.5a.75.75 0 0 1-1.5 0v-3.5Zm-2.75 1.5a.75.75 0 0 1 1.5 0v2a.75.75 0 0 1-1.5 0v-2Zm-2 .75a.75.75 0 0 0-.75.75v.5a.75.75 0 0 0 1.5 0v-.5a.75.75 0 0 0-.75-.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center">{$i18n.t('Leaderboard')}</div>
			</button>

			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab ===
				'feedbacks'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedTab = 'feedbacks';
				}}
			>
				<div class=" self-center mr-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M5.25 2A2.25 2.25 0 0 0 3 4.25v9a.75.75 0 0 0 1.183.613l1.692-1.195 1.692 1.195a.75.75 0 0 0 .866 0l1.692-1.195 1.693 1.195A.75.75 0 0 0 13 13.25v-9A2.25 2.25 0 0 0 10.75 2h-5.5Zm3.03 3.28a.75.75 0 0 0-1.06-1.06L4.97 6.47a.75.75 0 0 0 0 1.06l2.25 2.25a.75.75 0 0 0 1.06-1.06l-.97-.97h1.315c.76 0 1.375.616 1.375 1.375a.75.75 0 0 0 1.5 0A2.875 2.875 0 0 0 8.625 6.25H7.311l.97-.97Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center">{$i18n.t('Feedbacks')}</div>
			</button>
		</div>

		<div class="flex-1 mt-1 lg:mt-0 overflow-y-scroll">
			{#if selectedTab === 'leaderboard'}
				<Leaderboard {feedbacks} />
			{:else if selectedTab === 'feedbacks'}
				<Feedbacks {feedbacks} />
			{/if}
		</div>
	</div>

	<div
		class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5"
	>
		{#if (rankedModels ?? []).length === 0}
			<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-1">
				{$i18n.t('No models found')}
			</div>
		{:else}
			<table
				class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded"
			>
				<thead
					class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
				>
					<tr class="">
						<th scope="col" class="px-3 py-1.5 cursor-pointer select-none w-3">
							{$i18n.t('RK')}
						</th>
						<th scope="col" class="px-3 py-1.5 cursor-pointer select-none">
							{$i18n.t('Model')}
						</th>
						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
							{$i18n.t('Rating')}
						</th>
						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
							{$i18n.t('Won')}
						</th>

						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
							{$i18n.t('Draw')}
						</th>
						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
							{$i18n.t('Lost')}
						</th>
					</tr>
				</thead>
				<tbody class="">
					{#each rankedModels as model, modelIdx (model.id)}
						<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
							<td class="px-3 py-1.5 text-left font-medium text-gray-900 dark:text-white w-fit">
								<div class=" line-clamp-1">
									{model?.rating !== '-' ? modelIdx + 1 : '-'}
								</div>
							</td>
							<td class="px-3 py-1.5 flex flex-col justify-center">
								<div class="flex items-center gap-2">
									<div class="flex-shrink-0">
										<img
											src={model?.info?.meta?.profile_image_url ?? '/favicon.png'}
											alt={model.name}
											class="size-5 rounded-full object-cover shrink-0"
										/>
									</div>

									<div class="font-medium text-gray-800 dark:text-gray-200 pr-4">
										{model.name}
									</div>
								</div>
							</td>
							<td class="px-3 py-1.5 text-right font-medium text-gray-900 dark:text-white w-max">
								{model.rating}
							</td>

							<td class=" px-3 py-1.5 text-right font-semibold text-green-500">
								{model.stats.won}
							</td>

							<td class=" px-3 py-1.5 text-right font-semibold">
								{model.stats.draw}
							</td>

							<td class="px-3 py-1.5 text-right font-semibold text-red-500">
								{model.stats.lost}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>

	<div class="pb-4"></div>

	<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
		<div class="flex md:self-center text-lg font-medium px-0.5">
			{$i18n.t('Feedback History')}
		</div>
	</div>

	<div
		class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5"
	>
		{#if (feedbacks ?? []).length === 0}
			<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-1">
				{$i18n.t('No feedbacks found')}
			</div>
		{:else}
			<table
				class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded"
			>
				<thead
					class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
				>
					<tr class="">
						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-0">
							{$i18n.t('User')}
						</th>

						<th scope="col" class="px-3 py-1.5 cursor-pointer select-none">
							{$i18n.t('Models')}
						</th>

						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
							{$i18n.t('Result')}
						</th>

						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-0">
							{$i18n.t('Updated At')}
						</th>

						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-0"> </th>
					</tr>
				</thead>
				<tbody class="">
					{#each feedbacks as feedback (feedback.id)}
						<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
							<td class=" py-1 text-right font-semibold">
								<div class="flex justify-center">
									<Tooltip content={feedback?.user?.name}>
										<div class="flex-shrink-0">
											<img
												src={feedback?.user?.profile_image_url ?? '/user.png'}
												alt={feedback?.user?.name}
												class="size-5 rounded-full object-cover shrink-0"
											/>
										</div>
									</Tooltip>
								</div>
							</td>

							<td class="px-3 flex flex-col">
								<div class="flex flex-col items-start gap-0.5 h-full">
									<div class="flex flex-col h-full">
										{#if feedback.data?.sibling_model_ids}
											<div class="font-semibold text-gray-600 dark:text-gray-400 flex-1">
												{feedback.data?.model_id}
											</div>
											<div class=" text-[0.65rem] text-gray-600 dark:text-gray-400 line-clamp-1">
												{feedback.data.sibling_model_ids.join(', ')}
											</div>
										{:else}
											<div
												class=" text-sm font-medium text-gray-600 dark:text-gray-400 flex-1 py-2"
											>
												{feedback.data?.model_id}
											</div>
										{/if}
									</div>
								</div>
							</td>
							<td class="px-3 py-1 text-right font-medium text-gray-900 dark:text-white w-max">
								<div class=" flex justify-end">
									{#if feedback.data.rating.toString() === '1'}
										<Badge type="info" content={$i18n.t('Won')} />
									{:else if feedback.data.rating.toString() === '0'}
										<Badge type="muted" content={$i18n.t('Draw')} />
									{:else if feedback.data.rating.toString() === '-1'}
										<Badge type="error" content={$i18n.t('Lost')} />
									{/if}
								</div>
							</td>

							<td class=" px-3 py-1 text-right font-medium">
								{dayjs(feedback.updated_at * 1000).fromNow()}
							</td>

							<td class=" px-3 py-1 text-right font-semibold">
								<FeedbackMenu>
									<button
										class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
									>
										<EllipsisHorizontal />
									</button>
								</FeedbackMenu>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>

	<div class="pb-8"></div>
{/if}
