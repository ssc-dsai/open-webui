<script lang="ts">
	import { marked } from 'marked';
	import TurndownService from 'turndown';
	const turndownService = new TurndownService();

	import { onMount, onDestroy } from 'svelte';
	import { createEventDispatcher } from 'svelte';
	const eventDispatch = createEventDispatcher();

	import { EditorState, Plugin, TextSelection } from 'prosemirror-state';

	import { Editor } from '@tiptap/core';

	import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
	import Placeholder from '@tiptap/extension-placeholder';
	import Highlight from '@tiptap/extension-highlight';
	import Typography from '@tiptap/extension-typography';
	import StarterKit from '@tiptap/starter-kit';

	import { all, createLowlight } from 'lowlight';

	import { PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';

	// create a lowlight instance with all languages loaded
	const lowlight = createLowlight(all);

	export let className = 'input-prose';
	export let placeholder = 'Type here...';
	export let value = '';
	export let id = '';

	export let messageInput = false;
	export let shiftEnter = false;
	export let largeTextAsFile = false;

	export let id = '';
	export let value = '';
	export let placeholder = 'Type here...';
	export let trim = false;

	let element: HTMLElement; // Element where ProseMirror will attach
	let state;
	let view;

	// Plugin to add placeholder when the content is empty
	function placeholderPlugin(placeholder: string) {
		return new Plugin({
			props: {
				decorations(state) {
					const doc = state.doc;
					if (
						doc.childCount === 1 &&
						doc.firstChild.isTextblock &&
						doc.firstChild?.textContent === ''
					) {
						// If there's nothing in the editor, show the placeholder decoration
						const decoration = Decoration.node(0, doc.content.size, {
							'data-placeholder': placeholder,
							class: 'placeholder'
						});
						return DecorationSet.create(doc, [decoration]);
					}
					return DecorationSet.empty;
				}
			}
		});
	}

	function unescapeMarkdown(text: string): string {
		return text
			.replace(/\\([\\`*{}[\]()#+\-.!_>])/g, '$1') // unescape backslashed characters
			.replace(/&amp;/g, '&')
			.replace(/</g, '<')
			.replace(/>/g, '>')
			.replace(/&quot;/g, '"')
			.replace(/&#39;/g, "'");
	}

	// Custom parsing rule that creates proper paragraphs for newlines and empty lines
	function markdownToProseMirrorDoc(markdown: string) {
		// Split the markdown into lines
		const lines = markdown.split('\n\n');

		// Create an array to hold our paragraph nodes
		const paragraphs = [];

		// Process each line
		lines.forEach((line) => {
			if (line.trim() === '') {
				// For empty lines, create an empty paragraph
				paragraphs.push(schema.nodes.paragraph.create());
			} else {
				// For non-empty lines, parse as usual
				const doc = defaultMarkdownParser.parse(line);
				// Extract the content of the parsed document
				doc.content.forEach((node) => {
					paragraphs.push(node);
				});
			}
		});

		// Create a new document with these paragraphs
		return schema.node('doc', null, paragraphs);
	}

	// Create a custom serializer for paragraphs
	// Custom paragraph serializer to preserve newlines for empty paragraphs (empty block).
	function serializeParagraph(state, node: Node) {
		const content = node.textContent.trim();

		// If the paragraph is empty, just add an empty line.
		if (content === '') {
			state.write('\n\n');
		} else {
			state.renderInline(node);
			state.closeBlock(node);
		}
	}

	const customMarkdownSerializer = new defaultMarkdownSerializer.constructor(
		{
			...defaultMarkdownSerializer.nodes,

			paragraph: (state, node) => {
				serializeParagraph(state, node); // Use custom paragraph serialization
			}

			// Customize other block formats if needed
		},

		// Copy marks directly from the original serializer (or customize them if necessary)
		defaultMarkdownSerializer.marks
	);

	// Utility function to convert ProseMirror content back to markdown text
	function serializeEditorContent(doc) {
		const markdown = customMarkdownSerializer.serialize(doc);
		if (trim) {
			return unescapeMarkdown(markdown).trim();
		} else {
			return unescapeMarkdown(markdown);
		}
	}

	// ---- Input Rules ----
	// Input rule for heading (e.g., # Headings)
	function headingRule(schema) {
		return textblockTypeInputRule(/^(#{1,6})\s$/, schema.nodes.heading, (match) => ({
			level: match[1].length
		}));
	}

	// Input rule for bullet list (e.g., `- item`)
	function bulletListRule(schema) {
		return wrappingInputRule(/^\s*([-+*])\s$/, schema.nodes.bullet_list);
	}

	// Input rule for ordered list (e.g., `1. item`)
	function orderedListRule(schema) {
		return wrappingInputRule(/^(\d+)\.\s$/, schema.nodes.ordered_list, (match) => ({
			order: +match[1]
		}));
	}

	// Custom input rules for Bold/Italic (using * or _)
	function markInputRule(regexp: RegExp, markType: any) {
		return new InputRule(regexp, (state, match, start, end) => {
			const { tr } = state;
			if (match) {
				tr.replaceWith(start, end, schema.text(match[1], [markType.create()]));
			}
			return tr;
		});
	}

	function boldRule(schema) {
		return markInputRule(/(?<=^|\s)\*([^*]+)\*(?=\s|$)/, schema.marks.strong);
	}

	function italicRule(schema) {
		// Using lookbehind and lookahead to prevent the space from being consumed
		return markInputRule(/(?<=^|\s)_([^*_]+)_(?=\s|$)/, schema.marks.em);
	}

	// Initialize Editor State and View
	function afterSpacePress(state, dispatch) {
		// Get the position right after the space was naturally inserted by the browser.
		let { from, to, empty } = state.selection;

		if (dispatch && empty) {
			let tr = state.tr;

			// Check for any active marks at `from - 1` (the space we just inserted)
			const storedMarks = state.storedMarks || state.selection.$from.marks();

			const hasBold = storedMarks.some((mark) => mark.type === state.schema.marks.strong);
			const hasItalic = storedMarks.some((mark) => mark.type === state.schema.marks.em);

			// Remove marks from the space character (marks applied to the space character will be marked as false)
			if (hasBold) {
				tr = tr.removeMark(from - 1, from, state.schema.marks.strong);
			}
			if (hasItalic) {
				tr = tr.removeMark(from - 1, from, state.schema.marks.em);
			}

			// Dispatch the resulting transaction to update the editor state
			dispatch(tr);
		}

		return true;
	}

	function toggleMark(markType) {
		return (state, dispatch) => {
			const { from, to } = state.selection;
			if (state.doc.rangeHasMark(from, to, markType)) {
				if (dispatch) dispatch(state.tr.removeMark(from, to, markType));
				return true;
			} else {
				if (dispatch) dispatch(state.tr.addMark(from, to, markType.create()));
				return true;
			}
		};
	}

	function handleSpace(state, dispatch) {
		let { from, to, empty } = state.selection;

		if (dispatch && empty) {
			let tr = state.tr;

			// Check for any active marks at `from - 1` (the space we just inserted)
			const storedMarks = state.storedMarks || state.selection.$from.marks();

			const hasBold = storedMarks.some((mark) => mark.type === state.schema.marks.strong);
			const hasItalic = storedMarks.some((mark) => mark.type === state.schema.marks.em);

			console.log('Stored marks after space:', storedMarks, hasBold, hasItalic);

			// Remove marks from the space character (marks applied to the space character will be marked as false)
			if (hasBold) {
				tr = tr.removeMark(from - 1, from, state.schema.marks.strong);
			}
			if (hasItalic) {
				tr = tr.removeMark(from - 1, from, state.schema.marks.em);
			}

			// Dispatch the resulting transaction to update the editor state
			dispatch(tr);
		}

		return true;
	}

	function toggleMark(markType) {
		return (state, dispatch) => {
			const { from, to } = state.selection;
			if (state.doc.rangeHasMark(from, to, markType)) {
				if (dispatch) dispatch(state.tr.removeMark(from, to, markType));
				return true;
			} else {
				if (dispatch) dispatch(state.tr.addMark(from, to, markType.create()));
				return true;
			}
		};
	}

	function isInList(state) {
		const { $from } = state.selection;
		return (
			$from.parent.type === schema.nodes.paragraph && $from.node(-1).type === schema.nodes.list_item
		);
	}

	function isEmptyListItem(state) {
		const { $from } = state.selection;
		return isInList(state) && $from.parent.content.size === 0 && $from.node(-1).childCount === 1;
	}

	function exitList(state, dispatch) {
		return liftListItem(schema.nodes.list_item)(state, dispatch);
	}

	const options = {
		throwOnError: false
	};

	// Function to find the next template in the document
	function findNextTemplate(doc, from = 0) {
		const patterns = [
			{ start: '[', end: ']' },
			{ start: '{{', end: '}}' }
		];

		let result = null;

		doc.nodesBetween(from, doc.content.size, (node, pos) => {
			if (result) return false; // Stop if we've found a match
			if (node.isText) {
				const text = node.text;
				let index = Math.max(0, from - pos);
				while (index < text.length) {
					for (const pattern of patterns) {
						if (text.startsWith(pattern.start, index)) {
							const endIndex = text.indexOf(pattern.end, index + pattern.start.length);
							if (endIndex !== -1) {
								result = {
									from: pos + index,
									to: pos + endIndex + pattern.end.length
								};
								return false; // Stop searching
							}
						}
					}
					index++;
				}
			}
		});

		return result;
	}

	// Function to select the next template in the document
	function selectNextTemplate(state, dispatch) {
		const { doc, selection } = state;
		const from = selection.to;
		let template = findNextTemplate(doc, from);

		if (!template) {
			// If not found, search from the beginning
			template = findNextTemplate(doc, 0);
		}

		if (template) {
			if (dispatch) {
				const tr = state.tr.setSelection(TextSelection.create(doc, template.from, template.to));
				dispatch(tr);
			}
			return true;
		}
		return false;
	}

	export const setContent = (content) => {
		editor.commands.setContent(content);
	};

	const selectTemplate = () => {
		if (value !== '') {
			// After updating the state, try to find and select the next template
			setTimeout(() => {
				const templateFound = selectNextTemplate(editor.view.state, editor.view.dispatch);
				if (!templateFound) {
					// If no template found, set cursor at the end
					const endPos = editor.view.state.doc.content.size;
					editor.view.dispatch(
						editor.view.state.tr.setSelection(TextSelection.create(editor.view.state.doc, endPos))
					);
				}
			}, 0);
		}
	};

	onMount(() => {
		const content = marked.parse(value);
		editor = new Editor({
			element: element,
			extensions: [
				StarterKit,
				CodeBlockLowlight.configure({
					lowlight
				}),
				Highlight,
				Typography,
				Placeholder.configure({ placeholder })
			],
			content: content,
			autofocus: true,
			onTransaction: () => {
				// force re-render so `editor.isActive` works as expected
				editor = editor;

				const newValue = turndownService.turndown(editor.getHTML());
				if (value !== newValue) {
					value = newValue; // Trigger parent updates
				}
			},
			editorProps: {
				attributes: { id },
				handleDOMEvents: {
					focus: (view, event) => {
						eventDispatch('focus', { event });
						return false;
					},
					keypress: (view, event) => {
						eventDispatch('keypress', { event });
						return false;
					},

					keydown: (view, event) => {
						// Handle Tab Key
						if (event.key === 'Tab') {
							const handled = selectNextTemplate(view.state, view.dispatch);
							if (handled) {
								event.preventDefault();
								return true;
							}
						}

						if (messageInput) {
							if (event.key === 'Enter') {
								// Check if the current selection is inside a structured block (like codeBlock or list)
								const { state } = view;
								const { $head } = state.selection;

								// Recursive function to check ancestors for specific node types
								function isInside(nodeTypes: string[]): boolean {
									let currentNode = $head;
									while (currentNode) {
										if (nodeTypes.includes(currentNode.parent.type.name)) {
											return true;
										}
										if (!currentNode.depth) break; // Stop if we reach the top
										currentNode = state.doc.resolve(currentNode.before()); // Move to the parent node
									}
									return false;
								}

								const isInCodeBlock = isInside(['codeBlock']);
								const isInList = isInside(['listItem', 'bulletList', 'orderedList']);
								const isInHeading = isInside(['heading']);

								if (isInCodeBlock || isInList || isInHeading) {
									// Let ProseMirror handle the normal Enter behavior
									return false;
								}
							}

							// Handle shift + Enter for a line break
							if (shiftEnter) {
								if (event.key === 'Enter' && event.shiftKey) {
									editor.commands.setHardBreak(); // Insert a hard break
									view.dispatch(view.state.tr.scrollIntoView()); // Move viewport to the cursor
									event.preventDefault();
									return true;
								}
								if (event.key === 'Enter') {
									eventDispatch('enter', { event });
									event.preventDefault();
									return true;
								}
							}
							if (event.key === 'Enter') {
								eventDispatch('enter', { event });
								event.preventDefault();
								return true;
							}
						}
						eventDispatch('keydown', { event });
						return false;
					},
					paste: (view, event) => {
						if (event.clipboardData) {
							// Extract plain text from clipboard and paste it without formatting
							const plainText = event.clipboardData.getData('text/plain');
							if (plainText) {
								if (largeTextAsFile) {
									if (plainText.length > PASTED_TEXT_CHARACTER_LIMIT) {
										// Dispatch paste event to parent component
										eventDispatch('paste', { event });
										event.preventDefault();
										return true;
									}
								}
								return false;
							}

							// Check if the pasted content contains image files
							const hasImageFile = Array.from(event.clipboardData.files).some((file) =>
								file.type.startsWith('image/')
							);

							// Check for image in dataTransfer items (for cases where files are not available)
							const hasImageItem = Array.from(event.clipboardData.items).some((item) =>
								item.type.startsWith('image/')
							);
							if (hasImageFile) {
								// If there's an image, dispatch the event to the parent
								eventDispatch('paste', { event });
								event.preventDefault();
								return true;
							}

							if (hasImageItem) {
								// If there's an image item, dispatch the event to the parent
								eventDispatch('paste', { event });
								event.preventDefault();
								return true;
							}
						}

						// For all other cases (text, formatted text, etc.), let ProseMirror handle it
						view.dispatch(view.state.tr.scrollIntoView()); // Move viewport to the cursor after pasting
						return false;
					}
				}
			}
		});

		selectTemplate();
	});

	onDestroy(() => {
		if (editor) {
			editor.destroy();
		}
	});

	// Update the editor content if the external `value` changes
	$: if (editor && value !== turndownService.turndown(editor.getHTML())) {
		editor.commands.setContent(marked.parse(value)); // Update editor content
		selectTemplate();
	}
</script>

<div bind:this={element} class="relative w-full min-w-full h-full min-h-fit {className}" />
