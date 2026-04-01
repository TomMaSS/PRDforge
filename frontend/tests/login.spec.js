const { test, expect} = require( '@playwright/test');

test.describe('Login Page', ()=>{

    test('should load the login page',async({ page })=>{

    await page.goto('http://localhost:3000');
    await expect(page).toHaveTitle(/PRDforge/);
});

test('should show error with invalid credentials',async({ page })=>{

    await page.goto('http://localhost:3000');
    await page.fill('input[type="email"]','test@abc.com');
    await page.fill('input[type="password"]','testabc123');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Invalid email or password')).toBeVisible();
});

test('should not allow empty form submission',async({ page })=>{

    await page.goto('http://localhost:3000');
    await page.click('button[type="submit"]');
    await expect(page.locator('input[type="email"]')).toBeFocused();


})
});