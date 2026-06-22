-- 从 https://business.newcli.com/api/pricing 自动抓取
-- 价格单位: CNY / token (前端 *1000 显示为 /Kt)
-- 执行方式: docker exec -i llmrelay-postgres psql -U user -d llmrelay < scripts/seed_pricing.sql

INSERT INTO model_configs (model_id, manual_prompt_price, manual_completion_price, is_enabled)
VALUES
('claude-haiku-4-5-20251001', 0.0000073, 0.000073),
('claude-opus-4-1-20250805', 0.0001095, 0.000073),
('claude-opus-4-5-20251101', 0.0000365, 0.000073),
('claude-opus-4-5-20251101-thinking', 0.0000365, 0.000073),
('claude-opus-4-20250514', 0.0001095, 0.000073),
('claude-opus-4-6', 0.0000365, 0.000073),
('claude-opus-4-7', 0.0000365, 0.000073),
('claude-opus-4-8', 0.0000365, 0.000073),
('claude-sonnet-4-5-20250929', 0.0000219, 0.000073),
('claude-sonnet-4-5-20250929-thinking', 0.0000219, 0.000073),
('claude-sonnet-4-5', 0.0000219, 0.000073),
('claude-sonnet-4-20250514', 0.0000219, 0.000073),
('claude-sonnet-4-6', 0.0000219, 0.000073),
('claude-3-5-haiku-20241022', 0.0000073, 0.000073),
('claude-fable-5', 0.000073, 0.000073),
('gpt-5.4', 0.00001825, 0.0000876),
('gpt-5.4-mini', 0.000005475, 0.0000876),
('gpt-5.4-openai-compact', 0.0000219, 0.0000876),
('gpt-5.5', 0.0000365, 0.0000876),
('gpt-5.5-openai-compact', 0.0000365, 0.0000876),
('gemini-2.5-flash', 0.0000219, 0.000121667),
('gemini-2.5-flash-lite', 0.0000219, 0.0000584),
('gemini-2.5-pro', 0.0000219, 0.0001168),
('gemini-3-flash', 0.0000219, 0.0000876),
('gemini-3-flash-preview', 0.0000219, 0.0000876),
('gemini-3-pro', 0.0000219, 0.0000876),
('gemini-3-pro-high', 0.0000219, 0.0000876),
('gemini-3-pro-low', 0.0000219, 0.0000876),
('gemini-3-pro-preview', 0.0000219, 0.0000876),
('gemini-3.1-pro', 0.0000146, 0.0000876),
('gemini-3.1-pro-low', 0.0000146, 0.0000876),
('gemini-3.1-pro-preview', 0.0000146, 0.0000876),
('gemini-3.5-flash', 0.00001095, 0.0000876),
('gemini-3.5-flash-low', 0.00001095, 0.0000876),
('codex-auto-review', 0.00001825, 0.0000876)
ON CONFLICT (model_id) DO UPDATE SET
  manual_prompt_price = EXCLUDED.manual_prompt_price,
  manual_completion_price = EXCLUDED.manual_completion_price,
  is_enabled = true;
